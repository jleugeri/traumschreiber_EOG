import numpy as np
import matplotlib
matplotlib.use('qt5agg')
from matplotlib import pyplot as plt

data = np.genfromtxt('dump.csv', delimiter=', ')

eog = data[1:, 5:9]
print(eog.shape)

plt.figure()
dist = 200
plt.subplot(2, 1, 1)
for i in range(4):
    dat = eog[:, i]
    dat[np.abs(dat) > 500] = np.nan
    plt.plot(eog[:, i] + i*dist, label='ch{}'.format(i))

plt.ylim(-500, 500+3*dist)
plt.legend()
plt.subplot(2, 1, 2)
plt.plot(data[1:, 9], label='x')
plt.plot(data[1:, 10], label='y')
plt.legend()
plt.show()

