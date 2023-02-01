import sys, subprocess, json, os

def is_external(path):
    return path.startswith("external/") or path.find("/bin/external/") != -1

refresh_compile_commands=sys.argv[1]
workspace_dir = os.getenv('BUILD_WORKSPACE_DIRECTORY')

subprocess.call(refresh_compile_commands, shell=True)

with open(workspace_dir + "/compile_commands.json", "r+") as compile_commands_file:
    compile_commands = json.load(compile_commands_file)

    for compile_command in compile_commands:
        args = compile_command["arguments"]
        for i in range(len(args)):
            if (args[i] == "-iquote" or args[i] == "-I") and is_external(args[i+1]):
                args[i] = "-isystem"
            elif (args[i] == "-isystem" or args[i] == "-iquote") and not is_external(args[i+1]):
                args[i] = "-I"

    compile_commands_file.truncate(0)
    compile_commands_file.seek(0)
    json.dump(
        compile_commands,
        compile_commands_file,
        indent=2,
        check_circular=False
    )

