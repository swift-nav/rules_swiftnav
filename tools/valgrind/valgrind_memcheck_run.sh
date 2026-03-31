#!/bin/bash
# Generic valgrind runner used by swift_add_valgrind_memcheck Bazel targets.
# All arguments are forwarded directly to valgrind:
#   [valgrind_flags...] binary [binary_args...]
#
# XML reports and logs are written to TEST_UNDECLARED_OUTPUTS_DIR so Bazel
# collects them as undeclared test outputs (visible in the test result).

XML_FILE="${TEST_UNDECLARED_OUTPUTS_DIR}/valgrind-memcheck.%p.xml"

valgrind \
    "--xml=yes" \
    "--xml-file=${XML_FILE}" \
    "$@"
EXIT_CODE=$?

if [ ${EXIT_CODE} -ne 0 ]; then
    echo "Valgrind reported errors. See XML report for details: ${XML_FILE}\n"
    cat "${TEST_UNDECLARED_OUTPUTS_DIR}"/valgrind-memcheck.*.xml
fi

exit ${EXIT_CODE}

