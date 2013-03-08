#!/usr/bin/env python
# Copyright (c) 2012 Cloudera, Inc. All rights reserved.
# py.test configuration module
#
import logging
from common.test_result_verifier import QueryTestResult

logging.basicConfig(level=logging.INFO, format='%(threadName)s: %(message)s')
LOG = logging.getLogger('test_configuration')

def pytest_addoption(parser):
  """Adds a new command line options to py.test"""
  parser.addoption("--exploration_strategy", default="core", help="Default exploration "\
                   "strategy for all tests. Valid values: core, pairwise, exhaustive.")

  parser.addoption("--workload_exploration_strategy", default=None, help=\
                   "Override exploration strategy for specific workloads using the "\
                   "format: workload:exploration_strategy. Ex: tpch:core,tpcds:pairwise.")

  parser.addoption("--impalad", default="localhost:21000", help=\
                   "The impalad host:port to run tests against.")

  parser.addoption("--hive_server", default="localhost:10000", help=\
                   "The hive server host:port to connect to.")

  parser.addoption("--update_results", action="store_true", default=False, help=\
                   "If set, will generate new results for all tests run instead of "\
                   "verifying the results.")

  parser.addoption("--table_formats", dest="table_formats", default=None, help=\
                   "Override the test vectors and run only using the specified table "\
                   "formats. Ex. --table_formats=seq/snap/block,text/none")

  parser.addoption("--hive_service_name", dest="hive_service_name",
                   default="Hive Metastore Server", help="The principal service name "\
                   "for the hive metastore client when using kerberos.")

  parser.addoption("--use_kerberos", action="store_true", default=False,
                   help="Use kerberos transport for running tests")

def pytest_assertrepr_compare(op, left, right):
  """
  Provides a hook for outputting type-specific assertion messages

  Expected to return a list or strings, where each string will be printed as a new line
  in the result output report on assertion failure.
  """
  if isinstance(left, QueryTestResult) and isinstance(right, QueryTestResult)\
        and op == "==":
    result = ['Comparing QueryTestResults (expected vs actual):']
    for l, r in map(None, left.rows, right.rows):
      result.append("%s == %s" % (l, r) if l == r else "%s != %s" % (l, r))
    if len(left.rows) != len(right.rows):
      result.append('Number of rows returned (expected vs actual): %d != %d' %\
          (len(left.rows), len(right.rows)))

    # pytest has a bug/limitation where it will truncate long custom assertion messages
    # (it has a hardcoded string length limit of 80*8 characters). To ensure this info
    # isn't lost, always log the assertion message.
    LOG.error('\n'.join(result))
    return result

def pytest_xdist_setupnodes(config, specs):
  """Hook that is called when setting up the xdist plugin"""
  # Force the xdist plugin to be quiet. In verbose mode it spews useless information.
  config.option.verbose = 0

def pytest_generate_tests(metafunc):
  """
  This is a hook to parameterize the tests based on the input vector.

  If a test has the 'vector' fixture specified, this code is invoked and it will build
  a set of test vectors to parameterize the test with.
  """
  if 'vector' in metafunc.fixturenames:
    metafunc.cls.add_test_dimensions()
    vectors = metafunc.cls.TestMatrix.generate_test_vectors(
        metafunc.config.option.exploration_strategy)
    if len(vectors) == 0:
      LOG.warning('No test vectors generated. Check constraints and input vectors')

    vector_names = map(str, vectors)
    # In the case this is a test result update, just select a single test vector to run
    # the results are expected to be the same in all cases
    if metafunc.config.option.update_results:
      vectors = vectors[0:1]
      vector_names = vector_names[0:1]
    metafunc.parametrize('vector', vectors, ids=vector_names)
