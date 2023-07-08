from perlin_noise import PerlinNoise
from time import time
from datetime import timedelta
import numpy as np
import sqlite3
from random import random


# generate 24 hours of data, 2 points per second
def generate_test_data():
    conn = sqlite3.connect('test.sqlite3')
    with conn:
        conn.execute('DROP TABLE IF EXISTS motion_logs')
        conn.execute('CREATE TABLE motion_logs ( time FLOAT, motion FLOAT )')

    noise = PerlinNoise(seed=time(), octaves=3)
    day_length = int(2 * timedelta(days=1).total_seconds())
    with conn:
        now = time()
        t = time() - timedelta(days=1).total_seconds()
        for i in range(day_length):
            if random() < 0.95:
                n = max(0, noise(i/day_length))
                conn.execute('INSERT INTO motion_logs (time, motion) VALUES (?, ?)', (t, n))
            t += 0.5
            if t > now:
                break

# generate sums for each interval over the last 24 hours
def generate_sums(num_chunks: int, conn: sqlite3.Connection):
    interval = timedelta(days=1/num_chunks).total_seconds()
    num_logs_expected = interval * 2 # there are expected to be 2 logs per second (max)
    now = time()
    t1 = now - timedelta(days=1).total_seconds()
    # remove old logs
    with conn:
        conn.execute('DELETE FROM motion_logs WHERE time < ?', [t1])
    # gather motion data
    motion_data = []
    while t1 < now:
        # get sum of all logs in the given time interval
        with conn:
            res = conn.execute('SELECT COUNT(motion), SUM(motion) FROM motion_logs WHERE time >= ? AND time < ?', (t1, t1+interval))
        num_logs, motion_sum = res.fetchall()[0]
        t1 += interval
        # if no logs found for this time interval, sum is 0
        if not num_logs:
            motion_data.append(0)
            continue
        # calculate weighted sum to account for potential missing logs
        motion_sum = num_logs_expected / num_logs * motion_sum
        motion_data.append(motion_sum)
    return motion_data

if __name__ == '__main__':
    generate_test_data()
    print( generate_sums(num_chunks=24, conn=sqlite3.connect('test.sqlite3')) )
