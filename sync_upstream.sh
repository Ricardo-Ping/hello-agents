#!/usr/bin/env bash

# 从上游仓库合并最新提交，同时保护本地提交和未提交修改。
# 在项目根目录运行：
#   ./sync_upstream.sh
#
# 指定其他上游分支：
#   ./sync_upstream.sh <上游分支>

set -u

UPSTREAM_NAME="upstream"
UPSTREAM_URL="https://github.com/datawhalechina/Hello-Agents.git"
UPSTREAM_BRANCH="${1:-main}"

die() {
    printf '错误：%s\n' "$*" >&2
    exit 1
}

command -v git >/dev/null 2>&1 || die "未找到 git 命令。"

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || die "当前目录不在 Git 仓库中。"
cd "$REPO_ROOT" || die "无法进入仓库根目录：$REPO_ROOT"

CURRENT_BRANCH=$(git symbolic-ref --quiet --short HEAD) || die "当前处于 detached HEAD 状态，请先切换到一个分支。"

# 避免干扰用户正在处理的 Git 操作。
GIT_DIR=$(git rev-parse --git-dir)
if [ -f "$GIT_DIR/MERGE_HEAD" ] || [ -d "$GIT_DIR/rebase-merge" ] || [ -d "$GIT_DIR/rebase-apply" ] || [ -f "$GIT_DIR/CHERRY_PICK_HEAD" ]; then
    die "仓库中存在尚未完成的 merge、rebase 或 cherry-pick，请先处理它。"
fi

if git remote get-url "$UPSTREAM_NAME" >/dev/null 2>&1; then
    CONFIGURED_URL=$(git remote get-url "$UPSTREAM_NAME")
    if [ "$CONFIGURED_URL" != "$UPSTREAM_URL" ]; then
        die "远程 '$UPSTREAM_NAME' 当前指向 $CONFIGURED_URL，而不是预期的 $UPSTREAM_URL。"
    fi
else
    printf "添加上游远程：%s -> %s\n" "$UPSTREAM_NAME" "$UPSTREAM_URL"
    git remote add "$UPSTREAM_NAME" "$UPSTREAM_URL" || die "添加 upstream 失败。"
fi

printf "抓取 %s/%s...\n" "$UPSTREAM_NAME" "$UPSTREAM_BRANCH"
git fetch "$UPSTREAM_NAME" "$UPSTREAM_BRANCH" --prune || die "抓取上游提交失败。"
git show-ref --verify --quiet "refs/remotes/$UPSTREAM_NAME/$UPSTREAM_BRANCH" \
    || die "上游分支 $UPSTREAM_NAME/$UPSTREAM_BRANCH 不存在。"

# stash 同时保存已暂存、未暂存和未跟踪文件；不会保存被 .gitignore 忽略的文件。
STASHED=0
if [ -n "$(git status --porcelain)" ]; then
    STASH_MESSAGE="sync-upstream: preserve local changes on $CURRENT_BRANCH"
    printf "临时保存本地未提交修改...\n"
    git stash push --include-untracked --message "$STASH_MESSAGE" \
        || die "无法保存本地未提交修改，尚未执行合并。"
    STASHED=1
fi

printf "将 %s/%s 合并到 %s...\n" "$UPSTREAM_NAME" "$UPSTREAM_BRANCH" "$CURRENT_BRANCH"
if ! git merge --no-edit "$UPSTREAM_NAME/$UPSTREAM_BRANCH"; then
    printf "上游合并发生冲突，正在中止合并并恢复原工作区...\n" >&2
    git merge --abort || die "无法中止合并；本地修改仍保存在 stash 中。"

    if [ "$STASHED" -eq 1 ]; then
        git stash pop --index \
            || die "合并已中止，但自动恢复本地修改失败；修改仍保存在 stash 中，请运行 git stash list 查看。"
    fi
    die "未合并上游提交；本地提交和未提交修改均已保留。"
fi

if [ "$STASHED" -eq 1 ]; then
    printf "恢复本地未提交修改...\n"
    if ! git stash pop --index; then
        die "上游已合并，但恢复本地修改时发生冲突。stash 备份仍然保留，请解决冲突后检查 git stash list。"
    fi
fi

printf "完成：已将 %s/%s 合并到 %s，本地提交和未提交修改均已保留。\n" \
    "$UPSTREAM_NAME" "$UPSTREAM_BRANCH" "$CURRENT_BRANCH"
git status --short --branch
