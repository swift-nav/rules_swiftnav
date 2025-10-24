#include "add.hpp"
#include "gtest/gtest.h"

TEST(BaseMathTest, Add) {
  EXPECT_EQ(add(1, 2), 3);
  EXPECT_EQ(add(-1, 1), 0);
  EXPECT_EQ(add(-1, -1), -2);
}
