# https://specs.optimism.io/protocol/derivation.html
import rlp, zlib

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

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

decomp = zlib.decompressobj()
result = decomp.decompress(channel)

print("result of %d bytes: %s..." % (len(result), result.hex()[:100]))


