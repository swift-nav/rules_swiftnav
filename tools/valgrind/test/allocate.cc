// A binary with a known peak heap and a data dependency, so the valgrind macros
// have something to measure and something whose runfiles must resolve.

#include <cstdio>
#include <cstdlib>
#include <vector>

int main(int argc, char **argv) {
  if (argc > 1) {
    FILE *input = fopen(argv[1], "r");
    if (input == nullptr) {
      fprintf(stderr, "could not open %s\n", argv[1]);
      return 1;
    }
    fclose(input);
  }

  std::vector<char> block(4 * 1024 * 1024, 1);
  printf("allocated %zu bytes\n", block.size());
  return block[0] == 1 ? 0 : 1;
}
