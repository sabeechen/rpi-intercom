import pytest
import numpy as np

from rpi_intercom.circular_buffer import Buffer

def test_basic_buffer():
    buffer = Buffer(5)
    buffer.push(np.array([0, 1, 2]))
    buffer.length == 3
    np.testing.assert_array_equal(buffer.read(3), [0, 1, 2])
    np.testing.assert_array_equal(buffer.pop(3), [0, 1, 2])
    np.testing.assert_array_equal(buffer.pop(3), [])

    buffer.push(np.array([1, 2, 3, 4]))
    np.testing.assert_array_equal(buffer.read(1), [1])
    np.testing.assert_array_equal(buffer.read(3), [1, 2, 3])
    np.testing.assert_array_equal(buffer.read(10), [1, 2, 3, 4])

    buffer.push(np.array([5]))
    np.testing.assert_array_equal(buffer.read(1), [1])
    np.testing.assert_array_equal(buffer.read(3), [1, 2, 3])
    np.testing.assert_array_equal(buffer.read(10), [1, 2, 3, 4, 5])

    buffer.push(np.array([6, 7, 8]))
    np.testing.assert_array_equal(buffer.read(10), [4, 5, 6, 7, 8])

    buffer.push(np.array([9]))
    np.testing.assert_array_equal(buffer.read(10), [5, 6, 7, 8, 9])
    np.testing.assert_array_equal(buffer.read(5), [5, 6, 7, 8, 9])
    np.testing.assert_array_equal(buffer.read(4), [5, 6, 7, 8])

    buffer.push(np.array([10, 11]))
    np.testing.assert_array_equal(buffer.read(10), [7, 8, 9, 10, 11])
    np.testing.assert_array_equal(buffer.read(5), [7, 8, 9, 10, 11])
    np.testing.assert_array_equal(buffer.read(4), [7, 8, 9, 10])

    buffer.push(np.array([12, 13]))
    np.testing.assert_array_equal(buffer.read(10), [9, 10, 11, 12, 13])
    np.testing.assert_array_equal(buffer.read(5), [9, 10, 11, 12, 13])
    np.testing.assert_array_equal(buffer.read(4), [9, 10, 11, 12])

    buffer.push(np.array([14, 15]))
    np.testing.assert_array_equal(buffer.read(10), [11, 12, 13, 14, 15])
    np.testing.assert_array_equal(buffer.read(5), [11, 12, 13, 14, 15])
    np.testing.assert_array_equal(buffer.read(4), [11, 12, 13, 14])

    buffer.push(np.array([16, 17, 18]))
    np.testing.assert_array_equal(buffer.read(10), [14, 15, 16, 17, 18])
    np.testing.assert_array_equal(buffer.read(5), [14, 15, 16, 17, 18])
    np.testing.assert_array_equal(buffer.read(4), [14, 15, 16, 17])

    buffer.push(np.array([19, 20, 21]))
    np.testing.assert_array_equal(buffer.read(10), [17, 18, 19, 20, 21])
    np.testing.assert_array_equal(buffer.read(5), [17, 18, 19, 20, 21])
    np.testing.assert_array_equal(buffer.read(4), [17, 18, 19, 20])

    np.testing.assert_array_equal(buffer.pop(3), [17, 18, 19])
    np.testing.assert_array_equal(buffer.read(5), [20, 21])

    np.testing.assert_array_equal(buffer.pop(1), [20])
    np.testing.assert_array_equal(buffer.read(5), [21])

    np.testing.assert_array_equal(buffer.pop(5), [21])
    np.testing.assert_array_equal(buffer.read(5), [])

    buffer.push(np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]))
    np.testing.assert_array_equal(buffer.read(5), [6, 7, 8, 9, 10])
    
    buffer.push(np.array([11, 12, 13]))
    np.testing.assert_array_equal(buffer.read(5), [9, 10, 11, 12, 13])
    np.testing.assert_array_equal(buffer.pop(10), [9, 10, 11, 12, 13])
    assert buffer.length == 0

    buffer.push(np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]))
    buffer.push(np.array([11, 12, 13]))
    buffer.push(np.array([14, 15, 16]))
    np.testing.assert_array_equal(buffer.pop(1), [12])
    np.testing.assert_array_equal(buffer.pop(1), [13])
    np.testing.assert_array_equal(buffer.pop(1), [14])
    np.testing.assert_array_equal(buffer.pop(1), [15])
    np.testing.assert_array_equal(buffer.pop(1), [16])
    assert buffer.length == 0

    buffer.push(np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]))
    buffer.push(np.array([11, 12, 13]))
    buffer.push(np.array([14, 15, 16]))
    np.testing.assert_array_equal(buffer.pop(2), [12, 13])
    np.testing.assert_array_equal(buffer.pop(2), [14, 15])
    np.testing.assert_array_equal(buffer.pop(2), [16])
    assert buffer.length == 0

    buffer.push(np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]))
    buffer.push(np.array([11, 12, 13]))
    buffer.push(np.array([14, 15, 16]))
    np.testing.assert_array_equal(buffer.pop(3), [12, 13, 14])
    np.testing.assert_array_equal(buffer.pop(3), [15, 16])
    assert buffer.length == 0