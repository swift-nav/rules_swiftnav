#include "use_external_dep.hpp"

double compute_dot_product(const Eigen::Vector3d& a, const Eigen::Vector3d& b) {
  return a.dot(b);
}

double compute_magnitude(const Eigen::Vector3d& v) {
  return v.norm();
}
