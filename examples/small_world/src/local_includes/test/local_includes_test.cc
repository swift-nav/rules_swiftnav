#include <gtest/gtest.h>
#include <local_includes/counter.hpp>
#include <local_includes/limit.hpp>

TEST(LocalIncludes, NextCount) { EXPECT_EQ(small_world::next_count(41), 42); }

TEST(LocalIncludes, GeneratedLimit) { EXPECT_EQ(small_world::limit(), 99); }
