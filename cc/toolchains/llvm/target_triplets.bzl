X86_64_LINUX = "x86_64-unknown-linux-gnu"
AARCH64_LINUX = "aarch64-unknown-linux-gnu"
X86_64_DARWIN = "x86_64-apple-macosx"
AARCH64_DARWIN = "aarch64-apple-macosx"
X86_64_WINDOWS = "x86_64-unknown-windows-gnu"

def is_target_triplet(target):
    return target != X86_64_LINUX or \
           target != AARCH64_LINUX or \
           target != X86_64_DARWIN or \
           target != AARCH64_DARWIN or \
           target != X86_64_WINDOWS
