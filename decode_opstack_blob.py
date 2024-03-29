# https://specs.optimism.io/protocol/derivation.html
import rlp, zlib

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# blobs from this tx: https://etherscan.io/tx/0x353c6f31903147f8d490c28e556caafd7a9fad8b3bc4fd210ae800ee24749adb
blobs = open("opstack_blobs_19538908.bin", "rb").read()

data = b""
for blob in chunks(blobs, 131072):
    assert blob[1] == 0
    declared_length = int.from_bytes(blob[2:5])
    print("found version 0 blob, declared length:", declared_length)
    blob_data = b""
    for chunk in chunks(blob, 128): # split into chunks 4 field elements each
        a = int.from_bytes(chunk[:32])
        b = int.from_bytes(chunk[32:64])
        c = int.from_bytes(chunk[64:96])
        d = int.from_bytes(chunk[96:128])
        assert (a | b | c | d) >> 254 == 0 # spec forces all elements to be max 254 bits
        # helluva encoding (i won't comment this shit just copypaste it if you need it for your project)
        a_dec = (((a & ((1 << 248) - 1)) << 8) | (a >> 248) | ((b >> 252) << 6)).to_bytes(32)
        b_dec = (((b & ((1 << 248) - 1)) << 8) | ((b >> 248) & ((1 << 4) - 1)) | (((d >> 248) & ((1 << 4) - 1)) << 4)).to_bytes(32)
        c_dec = (((c & ((1 << 248) - 1)) << 8) | (c >> 248) | ((d >> 252) << 6)).to_bytes(32)
        d_dec = chunk[97:128]
        blob_data += a_dec + b_dec + c_dec + d_dec
    
    data += blob_data[4:declared_length+4]

print("decoded blobs into %d bytes raw data" % len(data))
channel = b""
while data != b"":
    assert data[0] == 0 # frame version
    frame_length = int.from_bytes(data[19:23])
    print("frame data length:", frame_length)
    print("index", int.from_bytes(data[17:19]))
    print("is last:", data[23+frame_length])

    channel += data[23:23+frame_length]
    data = data[24+frame_length:]

print("channel data length:", len(channel))
zlib.decompress(channel)