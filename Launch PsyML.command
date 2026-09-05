#!/bin/zsh
# Finder-friendly launcher; use the project's Python environment.
cd -- "${0:A:h}" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if [[ -x .venv/bin/python ]]; then
    .venv/bin/python tools/launch_gui.py
elif command -v uv >/dev/null 2>&1; then
    uv run python tools/launch_gui.py
else
    print '未找到项目 Python 环境。请先按 README 完成安装。'
    print 'Project Python environment unavailable. Follow README installation steps.'
    read -r '?按回车关闭 / Press Enter to close'
    exit 1
fi
psyml_launch_exit=$?
if (( psyml_launch_exit != 0 )); then
    print '启动失败，请保留上方错误信息。 / Launch failed; keep the error above.'
    read -r '?按回车关闭 / Press Enter to close'
fi
exit "$psyml_launch_exit"
