#include "base_math.hpp"
#include "gtest/gtest.h"

TEST(BaseMathTest, Add) {
  EXPECT_EQ(add(1, 2), 3);
  EXPECT_EQ(add(-1, 1), 0);
  EXPECT_EQ(add(-1, -1), -2);
}

TEST(BaseMathTest, SignPlus) {
  EXPECT_EQ(Math::sign(10), 1);
}
