#include "old_folder_structure/old_folder_structure.hpp"
#include "gtest/gtest.h"

TEST(old_folder_structure, Minus) {
  EXPECT_EQ(minus(1, 2), -1);
  EXPECT_EQ(minus(-1, 1), -2);
  EXPECT_EQ(minus(-1, -1), 0);
}

TEST(old_folder_structure, InvSignPlus) {
  EXPECT_EQ(Math::inv_sign(10), -1);
}
