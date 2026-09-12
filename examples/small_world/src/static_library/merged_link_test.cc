#include "gtest/gtest.h"
#include "src/base_math/sign.hpp"
#include "src/fibonacci/fibonacci.hpp"

// Links against the merged archive produced by cc_static_library and exercises
// symbols from every library folded into it, including the transitive dep
// (add, via fibonacci).
TEST(MergedStaticLibraryTest, LinksTransitiveDeps) {
  EXPECT_EQ(fibonacci(10), 55);
  EXPECT_EQ(Math::sign(-3), -1);
}
