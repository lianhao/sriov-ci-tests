==================
sriov-ci-tests
==================

A Tempest plugin providing integration tests for SR-IOV features.

This plugin is run as part of the

Requirements
------------

The features tested are all dependent on underlying hardware support. As such,
the following platform features are required:

* NIC should support SR-IOV

Installation
------------

The plugin should be installed like any other package. Once installed, it will
be detected on subsequent runs of Temptest and enabled by default.

At the command line, run::

    $ pip install sriov-ci-tests

Or, if you have virtualenvwrapper installed, run::

    $ mkvirtualenv sriov-ci-tests
    $ pip install sriov-ci-tests

If you want to hack on the tests themselves, install them in editable mode
(setuptools develop mode)::

    $ pip install -e

Be aware that this package will not be available if running Tempest in a
different virtualenv, e.g. via a Tox target.

Usage
-----

All test commands should be run from the Tempest install directory, e.g.
``/opt/stack/tempest``.

To list all SR-IOV CI tempest cases, run::

    $ stestr list sriov_ci_tests

To run only these tests, run::

    $ stestr run sriov_ci_tests

Or via tox::

    $ tox -e all-plugin sriov_ci_tests

To run a single test case, run with test case name::

    $ stestr run sriov_ci_tests.tests.api.test_sriov_network_one_macvtap_port.TestNetworkAdvancedServerOps
