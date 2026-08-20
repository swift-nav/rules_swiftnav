#include <local_includes/counter.hpp>

#include "internal/detail.hpp"

namespace small_world {

int next_count(int value) { return detail::increment(value); }

}  // namespace small_world
