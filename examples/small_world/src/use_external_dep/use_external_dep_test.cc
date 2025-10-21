#include "use_external_dep.hpp"
#include "gtest/gtest.h"

TEST(UseExternalDepTest, DotProduct) {
  Eigen::Vector3d a(1.0, 2.0, 3.0);
  Eigen::Vector3d b(4.0, 5.0, 6.0);

  // Expected dot product: 1*4 + 2*5 + 3*6 = 4 + 10 + 18 = 32
  EXPECT_DOUBLE_EQ(compute_dot_product(a, b), 32.0);
}

TEST(UseExternalDepTest, DotProductOrthogonal) {
  Eigen::Vector3d a(1.0, 0.0, 0.0);
  Eigen::Vector3d b(0.0, 1.0, 0.0);

  // Orthogonal vectors have dot product of 0
  EXPECT_DOUBLE_EQ(compute_dot_product(a, b), 0.0);
}

TEST(UseExternalDepTest, Magnitude) {
  Eigen::Vector3d v(3.0, 4.0, 0.0);

  // Expected magnitude: sqrt(3^2 + 4^2) = sqrt(9 + 16) = sqrt(25) = 5
  EXPECT_DOUBLE_EQ(compute_magnitude(v), 5.0);
}

TEST(UseExternalDepTest, MagnitudeUnitVector) {
  Eigen::Vector3d v(1.0, 0.0, 0.0);

  // Unit vector has magnitude of 1
  EXPECT_DOUBLE_EQ(compute_magnitude(v), 1.0);
}
