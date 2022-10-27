<!-- Generated with Stardoc: http://skydoc.bazel.build -->



<a id="swift_cc_binary"></a>

## swift_cc_binary

<pre>
swift_cc_binary(<a href="#swift_cc_binary-kwargs">kwargs</a>)
</pre>

Wraps cc_binary to enforce standards for a production binary.

Primarily this consists of a default set of compiler options and
language standards. Production targets (swift_cc*), are compiled 
with the -pedantic flag.


**PARAMETERS**


| Name  | Description | Default Value |
| :------------- | :------------- | :------------- |
| <a id="swift_cc_binary-kwargs"></a>kwargs |  See https://bazel.build/reference/be/c-cpp#cc_binary<br><br>An additional attribute nocopts is supported. This attribute takes a list of flags to remove from the default compiler options. Use judiciously.   |  none |


<a id="swift_cc_library"></a>

## swift_cc_library

<pre>
swift_cc_library(<a href="#swift_cc_library-kwargs">kwargs</a>)
</pre>

Wraps cc_library to enforce standards for a production library.

Primarily this consists of a default set of compiler options and
language standards. Production targets (swift_cc*), are compiled 
with the -pedantic flag.


**PARAMETERS**


| Name  | Description | Default Value |
| :------------- | :------------- | :------------- |
| <a id="swift_cc_library-kwargs"></a>kwargs |  See https://bazel.build/reference/be/c-cpp#cc_library<br><br>An additional attribute nocopts is supported. This attribute takes a list of flags to remove from the default compiler options. Use judiciously.   |  none |


<a id="swift_cc_test"></a>

## swift_cc_test

<pre>
swift_cc_test(<a href="#swift_cc_test-name">name</a>, <a href="#swift_cc_test-type">type</a>, <a href="#swift_cc_test-kwargs">kwargs</a>)
</pre>

Wraps cc_test to enforce Swift testing conventions.

**PARAMETERS**


| Name  | Description | Default Value |
| :------------- | :------------- | :------------- |
| <a id="swift_cc_test-name"></a>name |  A unique name for this rule.   |  none |
| <a id="swift_cc_test-type"></a>type |  Specifies whether the test is a unit or integration test.<br><br>These are passed to cc_test as tags which enables running these test types seperately: <code>bazel test --test_tag_filters=unit //...</code>   |  none |
| <a id="swift_cc_test-kwargs"></a>kwargs |  See https://bazel.build/reference/be/c-cpp#cc_test   |  none |


<a id="swift_cc_test_library"></a>

## swift_cc_test_library

<pre>
swift_cc_test_library(<a href="#swift_cc_test_library-kwargs">kwargs</a>)
</pre>

Wraps cc_library to enforce Swift test library conventions.

**PARAMETERS**


| Name  | Description | Default Value |
| :------------- | :------------- | :------------- |
| <a id="swift_cc_test_library-kwargs"></a>kwargs |  See https://bazel.build/reference/be/c-cpp#cc_test   |  none |


<a id="swift_cc_tool"></a>

## swift_cc_tool

<pre>
swift_cc_tool(<a href="#swift_cc_tool-kwargs">kwargs</a>)
</pre>

Wraps cc_binary to enforce standards for a non-production binary.

Primarily this consists of a default set of compiler options and
language standards. Non-production targets (swift_cc_tool*), are 
compiled without the -pedantic flag.


**PARAMETERS**


| Name  | Description | Default Value |
| :------------- | :------------- | :------------- |
| <a id="swift_cc_tool-kwargs"></a>kwargs |  See https://bazel.build/reference/be/c-cpp#cc_binary<br><br>An additional attribute nocopts is supported. This attribute takes a list of flags to remove from the default compiler options. Use judiciously.   |  none |


<a id="swift_cc_tool_library"></a>

## swift_cc_tool_library

<pre>
swift_cc_tool_library(<a href="#swift_cc_tool_library-kwargs">kwargs</a>)
</pre>

Wraps cc_library to enforce standards for a non-production library.

Primarily this consists of a default set of compiler options and
language standards. Non-production targets (swift_cc_tool*), 
are compiled without the -pedantic flag.


**PARAMETERS**


| Name  | Description | Default Value |
| :------------- | :------------- | :------------- |
| <a id="swift_cc_tool_library-kwargs"></a>kwargs |  See https://bazel.build/reference/be/c-cpp#cc_library<br><br>An additional attribute nocopts is supported. This attribute takes a list of flags to remove from the default compiler options. Use judiciously.   |  none |


