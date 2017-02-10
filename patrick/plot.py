import numpy as np
import matplotlib
matplotlib.use('qt5agg')
from matplotlib import pyplot as plt

data = np.genfromtxt('data/run5.csv', delimiter=', ')

eog = data[1:, 2:5]
print(eog.shape)

plt.figure()
dist = 1000
plt.subplot(2, 1, 1)
for i in range(3):
    dat = eog[:, i]
    dat[np.abs(dat) > 1000] = np.nan
    plt.plot(eog[:, i] + i*dist, label='ch{}'.format(i))

plt.ylim(-1000, 1000+2*dist)
plt.legend()
plt.subplot(2, 1, 2)
plt.plot(data[1:, 9], label='x')
plt.plot(data[1:, 10], label='y')
plt.legend()
plt.show()

