#include "fibonacci.hpp"
#include "src/base_math/add.hpp"

int fibonacci(int n) {
  if (n <= 1) {
    return n;
  }
  return add(fibonacci(n - 1), fibonacci(n - 2));
}
