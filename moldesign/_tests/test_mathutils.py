import pytest

import numpy as np

from moldesign import mathutils
from moldesign import units as u
from moldesign.mathutils import spherical_harmonics as sh

from . import helpers


__PYTEST_MARK__ = 'internal'

CONSTRUCTORS = []
IDS = []


# Couldn't figure out a way to do this with fixtures ...
def constructor(f):
    def wrapper():
        arr, norm = f()
        return arr * 3.0 * u.nm, norm * 3.0 * u.nm
    wrapper.__name__ = f.__name__ + '_quantity'
    CONSTRUCTORS.append(f)
    IDS.append(f.__name__)
    CONSTRUCTORS.append(wrapper)
    IDS.append(wrapper.__name__)
    return wrapper


@constructor
def zeros():
    return np.zeros(3), 0.0


@constructor
def ones():
    return np.ones(3), np.sqrt(3)


@constructor
def y_unit_vector():
    v = np.zeros(3)
    v[1] = 1.0
    return v, 1.0


@constructor
def list_of_vectors():
    return np.array(TESTARRAY), np.array(TESTARRAY_NORMS)


@pytest.mark.parametrize('setupfn', CONSTRUCTORS, ids=IDS)
def test_norm(setupfn):
    arr, expected_norm = setupfn()
    n = mathutils.norm(arr)
    helpers.assert_almost_equal(n, expected_norm)


@pytest.mark.parametrize('setupfn', CONSTRUCTORS, ids=IDS)
def test_normalized(setupfn):
    arr, expected_norm = setupfn()
    vectorized = len(arr.shape) > 1
    normed = mathutils.normalized(arr)
    if not vectorized:
        arr, expected_norm, normed = [arr], [expected_norm], [normed]
    for v, n, unitvec in zip(arr, expected_norm, normed):
        if n != 0:
            helpers.assert_almost_equal(unitvec, v/n)


@pytest.mark.parametrize('setupfn', CONSTRUCTORS, ids=IDS)
@pytest.mark.screening
def test_perpendicular(setupfn):
    arr, expected_norm = setupfn()
    vectorized = len(arr.shape) > 1

    normvecs = mathutils.normalized(arr)
    perpvecs = mathutils.perpendicular(arr)
    assert isinstance(perpvecs, np.ndarray)
    assert not hasattr(perpvecs, 'units')

    # test that vectors are indeed perpendicular
    if vectorized:
        assert (np.abs((normvecs * perpvecs).sum(axis=1)) < 1e-12).all()
    else:
        assert abs(perpvecs.dot(normvecs)) < 1e-12

    # test that they are unit vectors (or 0 if the input vector is zero)
    if not vectorized:
        arr = [arr]
        perpvecs = [perpvecs]
        expected_norm = [expected_norm]

    for i, (vec, perpvec) in enumerate(zip(arr, perpvecs)):
        if expected_norm[i] == 0.0:
            assert mathutils.norm(perpvec) < 1e-12
        else:
            assert np.abs(1.0 - mathutils.norm(perpvec)) < 1e-12


def test_spherical_angles():
    assert sh.cart_to_polar_angles(np.zeros(3)) == (0.0, 0.0)

    oneangles = sh.cart_to_polar_angles(np.array([1.0, 0.0, 1.0]))
    np.testing.assert_allclose(np.array(oneangles),
                               np.array([np.pi/4, 0.0]))

    oneangles = sh.cart_to_polar_angles(np.array([0.0, 1.0, 1.0]))
    np.testing.assert_allclose(np.array(oneangles),
                               np.array([np.pi/4, np.pi/2.0]))

    np.testing.assert_allclose(np.array(sh.cart_to_polar_angles(RANDARRAY)),
                               np.array(RAND_ARRAY_ANGLES).T)


@pytest.mark.parametrize('shell', range(4))
def test_cart_and_spherical_equivalence(shell):
    l = shell

    testpoints = (np.random.rand(10, 3)-0.5)*10.0

    for m in range(-l,l+1):
        real_y = sh.Y(l, m)
        cart_y = sh.SPHERE_TO_CART[l,m]

        # single point
        np.testing.assert_allclose(real_y(testpoints[0]),
                                   cart_y(testpoints[0]),
                                   err_msg="Failed at %s" % ((l,m),))

        # vectorized
        np.testing.assert_allclose(real_y(testpoints),
                                   cart_y(testpoints),
                                   err_msg="Failed at %s" % ((l,m),))


RANDARRAY = np.array([[ 0.03047527, -4.49249374,  5.83154878],
                      [-7.38885486,  8.30076569, -7.97671261],
                      [ 6.79409582, -4.07664079,  8.45983794],
                      [-4.25045695,  0.03411114,  9.02986275]])

RAND_ARRAY_ANGLES = [(0.656426762, -1.564012833),
                     (2.1933588598416, 2.2981378887583),
                     (0.75266068344496, -0.54043933754409),
                     (0.43995560467481, 3.1335675381452)]


TESTARRAY = [[1.0,  0.0,  0.0],
             [0.0,  1.0,  0.0],
             [0.0,  0.0,  1.0],
             [0.0,  0.0,  0.0],
             [1.0,  -1.0,  1.0],
             [2.0,  2.0,  2.0],
             [0.57735027,  0.57735027,  -0.57735027],
             [0.70710678,  0.70710678,  0.],
             [0.0,  -1.0,  1.0]]

TESTARRAY_NORMS = [1.0, 1.0, 1.0, 0.0, np.sqrt(3), np.sqrt(12.0), 1.0, 1.0, np.sqrt(2)]