# https://specs.optimism.io/protocol/derivation.html
import rlp, zlib, io
from multiformats import varint

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def read_varint(b):
    r = b""
    while True:
        a = b.read(1)
        r += a
        if a[0] & 0b10000000 == 0:
            break
    return varint.decode(r)

def read_bitlist(l, b):
    r = []
    while l > 0:
        e = b.read(1)[0]
        rr = []
        for i in range(min(8, l)):
            rr.append(((e >> i) & 1) == 1)
        r.extend(rr[::-1])
        l -= 8
    return r

# blobs from this tx: https://etherscan.io/tx/0x353c6f31903147f8d490c28e556caafd7a9fad8b3bc4fd210ae800ee24749adb
blobs = open("opstack_blobs_19538908.bin", "rb").read()

datas = []
for blob in chunks(blobs, 131072):
    assert blob[1] == 0
    declared_length = int.from_bytes(blob[2:5])
    print("found version 0 blob, declared length:", declared_length)
    blob_data = b""
    for chunk in chunks(blob, 128): # split into chunks 4 field elements each

        byteA = chunk[32*0]
        byteB = chunk[32*1]
        byteC = chunk[32*2]
        byteD = chunk[32*3]

        assert (byteA | byteB | byteC | byteD) & 0b1100_0000 == 0
        tailA = chunk[32*0+1:32*1]
        tailB = chunk[32*1+1:32*2]
        tailC = chunk[32*2+1:32*3]
        tailD = chunk[32*3+1:32*4]
        
        x = (byteA & 0b0011_1111) | ((byteB & 0b0011_0000) << 2)
        y = (byteB & 0b0000_1111) | ((byteD & 0b0000_1111) << 4)
        z = (byteC & 0b0011_1111) | ((byteD & 0b0011_0000) << 2)
        
        result = b""
        result += tailA
        result += x.to_bytes(1)
        result += tailB
        result += y.to_bytes(1)
        result += tailC
        result += z.to_bytes(1)
        result += tailD
        
        assert len(result) == 4*31 + 3

        blob_data += result

    
    datas.append(blob_data[4:declared_length+4])

channel = b""
for data in datas:
    assert data[0] == 0 # derivation version
    data = data[1:] # strip prefix byte
    while data != b"":
        print("remaining data bytes: %d" % len(data))
        channel_id = data[0:16]
        print("channel:", channel_id.hex())
        frame_num = int.from_bytes(data[16:16+2])
        print("frame num: %d" % frame_num)
        frame_length = int.from_bytes(data[16+2:16+2+4])
        print("frame data length:", frame_length)
        end = 16+2+4+frame_length+1
        print("is_last:", data[end-1:end])
        frame_data = data[16+2+4:end-1]
        channel += frame_data
        data = data[end:]

decomp = zlib.decompressobj() # zlib.decompress() doesn't work for some reason
result = rlp.decode(decomp.decompress(channel))

print("result of %d bytes: %s...\n" % (len(result), result.hex()[:100]))
batch = io.BytesIO(result)
assert batch.read(1) == b"\x01", "decoded value is not a span batch"

print("timestamp since L2 genesis:", read_varint(batch))
print("last L1 origin number:", (read_varint(batch)))
print("parent L2 block hash:", batch.read(20).hex())
print("L1 origin block hash:", batch.read(20).hex())
l2_blocks_number = read_varint(batch)
print("number of L2 blocks:", l2_blocks_number)
print("how many were changed by L1 origin:", sum(read_bitlist(l2_blocks_number, batch)))
total_txs = sum([read_varint(batch) for _ in range(l2_blocks_number)])
print("total txs:", total_txs)
contract_creation_txs_number = sum(read_bitlist(total_txs, batch))
print("contract creation txs number:", contract_creation_txs_number)
y_parity_bits = read_bitlist(total_txs, batch)
tx_sigs = [batch.read(64) for _ in range(total_txs)]
tx_tos = [batch.read(20) for _ in range(total_txs)]
assert sum([int.from_bytes(to) == 0 for to in tx_tos]) == contract_creation_txs_number
# fuck python's pass by reference!!!
b = batch.read()
p = 0
legacy_txs_number = 0
tx_datas = []
for _ in range(total_txs):
    if b[p] in [1, 2]:
        p += 1
    else:
        legacy_txs_number += 1
    tx_datas.append(rlp.decode(b[p:], strict=False))
    p += sum(rlp.codec.consume_length_prefix(b[p:], 0)[2:])
batch = io.BytesIO(b)
batch.read(p)
print("legacy txs number:", legacy_txs_number)
tx_nonces = [read_varint(batch) for _ in range(total_txs)]
print("total gas limit in txs:", sum([read_varint(batch) for _ in range(total_txs)]))
print("number of EIP-155 protected legacy txs:", sum(read_bitlist(legacy_txs_number, batch)))