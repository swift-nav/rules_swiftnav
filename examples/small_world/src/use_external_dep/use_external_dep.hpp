#ifndef USE_EXTERNAL_DEP_HPP
#define USE_EXTERNAL_DEP_HPP

#include <Eigen/Dense>

// Compute the dot product of two 3D vectors using Eigen
double compute_dot_product(const Eigen::Vector3d& a, const Eigen::Vector3d& b);

// Compute the magnitude of a 3D vector using Eigen
double compute_magnitude(const Eigen::Vector3d& v);

#endif
