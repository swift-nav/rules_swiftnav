def swift_cc_library(**kwargs):
  """Wraps cc_library to enforce standards for a production library.
  """
    native.cc_library(**kwargs)

def swift_cc_tool_library(**kwargs):
  """Wraps cc_library to enforce standards for a non-production library.
  """
    native.cc_library(**kwargs)

def swift_cc_binary(**kwargs):
  """Wraps cc_binary to enforce standards for a production library.
  """
    native.cc_binary(**kwargs)

def swift_cc_tool(**kwargs):
  """Wraps cc_binary to enforce standards for a non-production library.
  """
    native.cc_binary(**kwargs)

def swift_cc_test(**kwargs):
  """Wraps cc_test to enforce Swift testing conventions.
  """
    native.cc_test(**kwargs)
