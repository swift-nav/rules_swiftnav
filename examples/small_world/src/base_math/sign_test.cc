#include "sign.hpp"
#include "gtest/gtest.h"

TEST(BaseMathTest, SignPlus) {
  EXPECT_EQ(Math::sign(10), 1);
  //EXPECT_EQ(Math::sign(-10), -1);
}
