# Coverage

on `x86_64 ubuntu`:

lcov:
```
bazel coverage --config=coverage_x86_64_linux //src/base_math:base_math_test

cp "$(bazel info output_path)/_coverage/_coverage_report.dat" cov.dat

genhtml --branch-coverage --output html cov.dat
```

Mac is not yet supported.
