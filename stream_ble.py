import pexpect
import datetime
import time
import numpy as np
import pandas


# Set up constants
plot = False

filename = "test_dump.csv"
device_addr = "20:73:7A:17:69:31"
chx_handle = b'0x010c'
characteristic_configuration_handle = "0x010b"
channel_names = ["ch{}".format(i) for i in range(8)]


def init(step=0):
    """ Initialize lines in plot """
    lines = ax.plot(np.zeros((10*250, 8))+np.nan)
    ax.set_xlim([0, 2500])
    ax.set_ylim([0, 18432])
    ax.set_yticks([2**11*i for i in range(1, 9)])
    return lines

if plot:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib import pyplot as pp
    import matplotlib.animation as animation

    # Plot lines
    fig, ax = pp.subplots()
    fig.show()
    fig.canvas.draw()

    lines = init()
    background = fig.canvas.copy_from_bbox(ax.bbox)


def parse(str):
    """ Parse the received package """
    buf = bytes((int(x, 16) for x in str.split(b' ')))
    return np.frombuffer(buf, dtype=np.int16)

# Start gatttool process in separate thread
# Corresponds to the command:
# > gatttool -b 20:73:7A:17:69:31 --char-write-req -a 0x010b --value=0100 --listen

child = pexpect.spawn("gatttool -b {addr} --char-write-req -a {hndl} --value=0100 --listen".format(addr=device_addr, hndl=characteristic_configuration_handle))


# Initialize variables
updated = {}
timestamps = {}
data = []#pandas.DataFrame()
dt = datetime.timedelta(seconds=0.1)
old_index = datetime.datetime.fromtimestamp(time.time())
# Run until <Ctrl-C>
try:
    print("waiting 5 seconds for device to set up ...")
    time.sleep(5)
    while True:
        # Try and if there is a TIMEOUT, retry
        try:
            child.expect("Notification handle = (\w+) value: ([0123456789abcdef ]*) \r\n", timeout=1)
            handle, value = child.match.groups()

            new_data = parse(value)
            new_index = datetime.datetime.fromtimestamp(time.time())

            if handle == chx_handle:
                s = pandas.Series(name=new_index, index=channel_names, data=new_data)
                data.append(s)
                #data = data.append(s)
            if new_index-old_index > dt:
                # Plot stuff
                pkgs_per_second = 0 if len(data) < 1000 else 1000/(data[-1].name - data[-1000].name).total_seconds()
                #pkgs_per_second = 0 if len(data)<1000 else 1000/(data.index[-1]-data.index[-1000]).total_seconds()
                print("pkgs/second: {}".format(pkgs_per_second))

                if plot:
                    fig.canvas.restore_region(background)
                    for i,line in enumerate(lines):
                        pts = data.values[-10*250:, i] + (i+1)*(2**11)
                        line.set_data(np.arange(len(pts)), pts)
                        ax.draw_artist(line)
                    fig.canvas.set_window_title("Data (received {} packages/second)".format(pkgs_per_second))
                    fig.canvas.blit(ax.bbox)

                old_index = new_index
        except pexpect.TIMEOUT:
            print("connection problems?")
            child.close()
            child = pexpect.spawn("gatttool -b {addr} --char-write-req -a {hndl} --value=0100 --listen".format(addr=device_addr, hndl=characteristic_configuration_handle))
except KeyboardInterrupt:
    pass

print("Converting to pandas.DataFrame...")
data = pandas.DataFrame(data=data)
data.to_csv(filename)
print("Stored in '" + filename + "'.")
