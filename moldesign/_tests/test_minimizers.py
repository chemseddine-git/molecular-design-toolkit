import collections

import numpy as np
import pytest

import moldesign as mdt
from .helpers import assert_something_resembling_minimization_happened
from moldesign import units as u


@pytest.fixture(scope='function')
def harmonic_atom():
    mol = mdt.Molecule([mdt.Atom(1)])
    mol.atoms[0].x = 2.0 * u.angstrom
    mol.set_energy_model(mdt.models.HarmonicOscillator, k=2.0*u.kcalpermol/u.angstrom**2)
    return mol


@pytest.mark.parametrize('MinClass', (mdt.min.GradientDescent,
                                      mdt.min.BFGS,
                                      mdt.min.SmartMin))
def test_basic_minimization(harmonic_atom, MinClass):
    mol = harmonic_atom
    e0 = mol.calculate_potential_energy()
    p0 = mol.positions.copy()

    minimizer = MinClass(mol)
    traj = minimizer()
    assert_something_resembling_minimization_happened(p0, e0, traj, mol)


@pytest.mark.parametrize('MinClass', (mdt.min.GradientDescent,
                                      mdt.min.BFGS,
                                      mdt.min.SmartMin))
def test_basic_minimization_remotely(harmonic_atom, MinClass):
    mol = harmonic_atom
    e0 = mol.calculate_potential_energy()
    p0 = mol.positions.copy()

    minimizer = MinClass(mol)
    traj = minimizer.runremotely()

    assert_something_resembling_minimization_happened(p0, e0, traj, mol)


MINIMIZERS = collections.OrderedDict([('gradient_descent', mdt.min.gradient_descent),
                                     ('leastsqr', mdt.min.sequential_least_squares),
                                     ('bfgs', mdt.min.bfgs),
                                     ('smart', mdt.min.minimize)])
# (ordered because pytest+xdist needs a definite ordering of parameters)


@pytest.mark.parametrize('minkey',(MINIMIZERS.keys()))
def test_constrained_distance_minimization(minkey):
    minimizer = MINIMIZERS[minkey]

    mol = mdt.Molecule([mdt.Atom(1), mdt.Atom(2)])
    mol.atoms[0].x = 2.0 * u.angstrom
    mol.atoms[1].x = 3.0 * u.angstrom
    mol.atoms[1].y = 2.0 * u.angstrom
    mol.set_energy_model(mdt.models.HarmonicOscillator, k=2.0*u.kcalpermol/u.angstrom**2)

    e0 = mol.calculate_potential_energy()
    p0 = mol.positions.copy()

    constraint = mol.constrain_distance(mol.atoms[0], mol.atoms[1])

    if minkey == 'bfgs':  # BFGS expected to fail here
        with pytest.raises(mdt.exceptions.NotSupportedError):
            minimizer(mol)
        return

    traj = minimizer(mol)

    assert_something_resembling_minimization_happened(p0, e0, traj, mol)
    assert abs(constraint.error()) < 1e-4 * u.angstrom

    # for scipy-based minimizers


@pytest.mark.parametrize('minkey',(MINIMIZERS.keys()))
def test_constrained_dihedral_minimization(minkey):
    minimizer = MINIMIZERS[minkey]
    mol = mdt.from_smiles('C=C')
    assert mol.atoms[0].atnum == mol.atoms[1].atnum == 6  # make sure we're picking the right atoms

    dihedral = mdt.DihedralMonitor(mol.atoms[0], mol.atoms[1])
    assert dihedral.value == 0.0

    dihedral.value = 45 * u.degrees
    constraint = dihedral.constrain()

    mol.set_energy_model(mdt.models.OpenBabelPotential, forcefield='mmff94s')
    e0_1 = mol.calculate_potential_energy()
    p0_1 = mol.positions.copy()

    if minkey == 'bfgs':  # BFGS expected to fail here
        with pytest.raises(mdt.exceptions.NotSupportedError):
            minimizer(mol)
        return

    traj = minimizer(mol, nsteps=100)
    assert_something_resembling_minimization_happened(p0_1, e0_1, traj, mol)

    assert constraint.error() <= 1.0 * u.degree
    traj_twists = traj.dihedral(mol.atoms[0], mol.atoms[1])
    assert (abs(traj_twists - 45 * u.degrees) <= 1.0 * u.degree).all()

    e0_2 = mol.potential_energy
    p0_2 = mol.positions.copy()
    mol.clear_constraints()
    traj2 = minimizer(mol, nsteps=100)

    assert_something_resembling_minimization_happened(p0_2, e0_2, traj2, mol)
    assert dihedral.value <= 5.0 * u.degrees


def _apply_noise(mol):
    noise = np.random.normal(size=(mol.num_atoms, 3), scale=0.05) * u.angstrom
    mol.positions += noise
