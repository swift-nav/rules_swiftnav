<!-- Generated with Stardoc: http://skydoc.bazel.build -->



<a id="configure_file"></a>

## configure_file

<pre>
configure_file(<a href="#configure_file-name">name</a>, <a href="#configure_file-out">out</a>, <a href="#configure_file-template">template</a>, <a href="#configure_file-vars">vars</a>)
</pre>


Equivalent of CMake's configure_file

Example:
  For the following CMake configure_file call:
  ```cmake
  set(MAX_CHANNELS "63")
  configure_file(config.h.in, config.h)
  ```

  The equivalent would be:
  ```starlark
  configure_file(
      name = "config",
      out = "config.h",
      template = "config.h.in",
      vars = { "MAX_CHANNELS":"63" }
  )
  ```


**ATTRIBUTES**


| Name  | Description | Type | Mandatory | Default |
| :------------- | :------------- | :------------- | :------------- | :------------- |
| <a id="configure_file-name"></a>name |  A unique name for this target.   | <a href="https://bazel.build/concepts/labels#target-names">Name</a> | required |  |
| <a id="configure_file-out"></a>out |  Name of the generated file.   | String | optional | <code>""</code> |
| <a id="configure_file-template"></a>template |  CMake style input template.   | <a href="https://bazel.build/concepts/labels">Label</a> | required |  |
| <a id="configure_file-vars"></a>vars |  Key values pairs to substitute.   | <a href="https://bazel.build/rules/lib/dict">Dictionary: String -> String</a> | optional | <code>{}</code> |


