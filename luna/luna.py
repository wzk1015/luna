import os
import time
import json
import getpass
import warnings
import sys
from pprint import pprint
from difflib import Differ
import filecmp

COMMANDS = ['install', 'init', 'commit', 'revise', 'reset', 'log', 'history', 'info', 'view', 'discard', 'delete','diff', 'makefile']

def install():
    from luna import __path__ as luna_path
    shell = os.environ["SHELL"]
    if shell.endswith("zsh"):
        shell_rc_path = "~/.zshrc"
    elif shell.endswith("bash"):
        shell_rc_path = "~/.bashrc"
    else:
        raise NotImplementedError("unknown shell: " + shell)
    luna_src_path = os.path.join(luna_path[0], "luna.py")
    scripts = [
        "alias luna=lunacore \$@",
        "lunacore()",
        "{",
        f"  python '{luna_src_path}' \$@",
        "}"
    ]

    msg = os.popen(
        f"echo \"{scripts[0]}\" >> {shell_rc_path}; " + \
        f"echo \"{scripts[1]}\" >> {shell_rc_path}; " + \
        f"echo \"{scripts[2]}\" >> {shell_rc_path}; " + \
        f"echo \"{scripts[3]}\" >> {shell_rc_path}; " + \
        f"echo \"{scripts[4]}\" >> {shell_rc_path}; " + \
        f"source {shell_rc_path}"
    ).read()
    if msg:
        print("received system message:", msg)
    else:
        print("successfully installed luna to", shell_rc_path)


def _luna(path, *args):
    ans = os.path.join(path, ".luna", *args)
    return ans


def _write_meta(path, **kwargs):
    try:
        with open(_luna(path, "metadata.json"), "r") as f:
            meta = json.load(f)
        for k, v in kwargs.items():
            meta[k] = v
        with open(_luna(path, "metadata.json"), "w") as f:
            json.dump(meta, f)
    except FileNotFoundError:
        raise FileNotFoundError("Not a luna directory: " + str(path))


def _read_meta(path, key):
    try:
        with open(_luna(path, "metadata.json"), "r") as f:
            meta = json.load(f)
        if key is None:
            return meta
        return meta[key]
    except FileNotFoundError:
        raise FileNotFoundError("Not a luna directory: " + str(path))


def _get_details(path, version):
    details = _read_meta(path, "version_details")
    key = "version " + version
    if key not in details.keys():
        raise ValueError("Unknown version: " + version)
    return details


def _add_history(path, info):
    h = _read_meta(path, "history")
    h.append({
        "user": getpass.getuser(),
        "time": time.ctime(),
        "info": info,
    })
    _write_meta(path, history=h)


def init(path):
    try:
        _read_meta(path, "create_time")
        warnings.warn("Already a luna repo: " + str(path))
        return
    except FileNotFoundError:
        os.mkdir(_luna(path))
        os.mkdir(_luna(path, "versions"))
        with open(_luna(path, "metadata.json"), "w") as f:
            meta = {
                "create_time"    : time.ctime(),
                "creator"        : getpass.getuser(),
                "path"           : path,
                "num_versions"   : 0,
                "cur_version"    : 0,
                "version_details": {},
                "history"        : []
            }
            json.dump(meta, f)
        _add_history(path, "luna init at " + path)
        print("init luna repo at " + path)


def commit(path, msg):
    version = str(int(_read_meta(path, "num_versions")) + 1)
    details = _read_meta(path, "version_details")
    os.mkdir(_luna(path, "versions", version))
    os.chdir(path)
    os.popen("cp -r * '{}'".format(_luna(path, "versions", version))).close()
    details["version " + version] = {
        "creator": getpass.getuser(),
        "time"   : time.ctime(),
        "msg"    : msg,
    }
    _write_meta(path, num_versions=version, version_details=details, cur_version=version)
    _add_history(path, "luna commit version {} with message '{}'".format(version, msg))
    print("commit version " + version)


def revise(path, version, msg):
    version = str(version)
    details = _get_details(path, version)
    details["version " + version]["msg"] = msg
    _write_meta(path, version_details=details)
    _add_history(path, "luna revise version {} with message '{}'".format(version, msg))
    print("revise version " + version)


def reset(path, version=None):
    if version is None:
        version = _read_meta(path, "cur_version")
    version = str(version)
    _get_details(path, version)
    os.popen("mv '{}' '{}'".format(_luna(path), os.path.join(path, "..", ".luna_temp"))).close()
    os.chdir(path)
    os.popen("rm -rf ./*", "w").close()
    os.popen("mv '{}' '{}'".format(os.path.join(path, "..", ".luna_temp"), _luna(path))).close()
    os.chdir(_luna(path, "versions", version))
    os.popen("cp -r * '{}'".format(path)).close()
    _write_meta(path, cur_version=version)
    _add_history(path, "luna reset to version " + version)
    print("reset to version " + version)


def log(path):
    s = _read_meta(path, "version_details")
    if s:
        pprint(s)
    else:
        print("no commits, empty log")


def history(path):
    pprint(_read_meta(path, "history"))


def info(path):
    pprint(_read_meta(path, None))


def view(path, version):
    version = str(version)
    pprint(_get_details(path, version)["version " + version])


def discard(path):
    os.popen("rm -rf '{}'".format(_luna(path))).close()
    print("discard luna repo at " + path)


def delete(path, version):
    if version == _read_meta(path, "cur_version"):
        _write_meta(path, cur_version="deleted")
    os.popen("rm -rf '{}'".format(_luna(path, "versions", version))).close()
    details = _get_details(path, version)
    details.pop("version " + version)
    _write_meta(path, version_details=details)
    _add_history(path, "luna delete version {} ".format(version))
    print("delete version " + version)


def _diff_compare(in_lines1, in_lines2):
    l1 = in_lines1.split("\n")
    l2 = in_lines2.split("\n")
    d = Differ()
    result = list(d.compare(l1, l2))
    result = "\n".join(result)
    return result


def diff(path, version1=None, version2=None, file=None):
    def _replace(string):
        return string.replace(_luna(path), '').replace('/versions/', 'version') \
            .replace(r'\versions\ '[:-1], 'version')

    def _is_file(string):
        return string is not None and not string.isnumeric() and string != "-"

    def _diff_file(file1, file2):
        lines1, lines2 = "", ""
        unique_file = ""
        try:
            with open(file1, errors="ignore") as f1:
                lines1 = f1.read()
        except FileNotFoundError:
            unique_file = _replace(file1)
        try:
            with open(file2, errors="ignore") as f2:
                lines2 = f2.read()
        except FileNotFoundError:
            assert unique_file == ""
            unique_file = _replace(file2)
        if unique_file:
            print("unique file {}".format(unique_file))
        else:
            print("diff file {} {}".format(_replace(file1), _replace(file2)))
        print(_diff_compare(lines1, lines2))

    def _diff_recur(d: filecmp.dircmp, key, v1path, v2path):
        for f in d.__getattr__(key):
            _diff_file(os.path.join(v1path, f), os.path.join(v2path, f))
        for name, sd in d.subdirs.items():
            _diff_recur(sd, key, os.path.join(v1path, name), os.path.join(v2path, name))

    v1 = _read_meta(path, "cur_version") if version1 in [None, "-"] or _is_file(version1) else str(version1)
    v2 = "[not staged]" if version2 in [None, "-"] or _is_file(version2) else str(version2)
    dir1 = _luna(path, "versions", v1)
    dir2 = _luna(path, "versions", v2) if v2 != "[not staged]" else path
    file = version1 if _is_file(version1) else file
    file = version2 if version1 is not None and not _is_file(version1) and _is_file(version2) else file
    if file is not None:
        _diff_file(os.path.join(dir1, file), os.path.join(dir2, file))
    else:
        d = filecmp.dircmp(dir1, dir2, hide=[os.curdir, os.pardir, ".luna"], ignore=['.git', '.DS_Store'])
        v1, v2 = "Version " + v1 + (" (latest version)" if version1 in [None, "-"] else ""), \
                 ("Version " + v2 if v2 != "[not staged]" else "working directory")
        print("Comparing {} and {}".format(v1, v2))
        print("Overall diff".center(50, "-"))
        d.report_full_closure()
        print("Different files".center(50, "-"))
        _diff_recur(d, "diff_files", dir1, dir2)
        print((v1 + " unique files").center(50, "-"))
        _diff_recur(d, "left_only", dir1, dir2)
        print((v2 + " unique files").center(50, "-"))
        _diff_recur(d, "right_only", dir1, dir2)


def makefile(filepath, filename):
    os.popen("touch '{}'".format(os.path.join(filepath, filename))).close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Hi! I'm luna~\nplease give me a command by 'luna xxx'")
    elif sys.argv[1] not in COMMANDS:
        print(f"luna: unknown command '{sys.argv[1]}'")
    else:
        exec("{}('{}',{})".format(sys.argv[1], os.getcwd(),
                                  ",".join(["'" + arg + "'" for arg in sys.argv[2:]])))