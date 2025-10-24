#ifndef SIGN_HPP
#define SIGN_HPP

int add(int x, int y);

struct Math {
    static int sign(int x) {
        if (x >= 0) {
            return 1;
        } else {
            return -1;
        }
    }
};

#endif
