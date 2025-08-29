#ifndef OLD_FOLDER_STRUCTURE_HPP
#define OLD_FOLDER_STRUCTURE_HPP

int minus(int x, int y);

struct Math {
    static int inv_sign(int x) {
        if (x >= 0) {
            return -1;
        } else {
            return 1;
        }
    }
};

#endif
