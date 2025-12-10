#!/bin/bash

# Function to display the menu and get user's choice
show_menu() {
    echo "Git 小幫手"
    echo "請選擇要執行的操作："
    echo "1. 提交並推送本地變更 (原功能)"
    echo "2. 從遠端拉取最新程式碼"
    echo "q. 退出"
    read -p "請輸入選項: " choice
}

# Function for the original git operations (add, commit, push)
original_git_operations() {
    echo "--- 開始執行原有 Git 操作 (提交與推送) ---"
    git add .
    read -p "請輸入提交訊息: " commit_message
    if [ -z "$commit_message" ]; then
        echo "提交訊息不可為空，操作已取消。"
        return
    fi
    git commit -m "$commit_message"
    git push
    echo "--- 原有 Git 操作執行完畢 ---"
}

# Function to pull latest changes from remote, with upstream setting
pull_from_remote() {
    echo "--- 開始從遠端拉取最新變更 ---"

    # 檢查目前分支是否有設定追蹤的遠端分支
    # If the command fails, TRACKING_BRANCH will be empty
    TRACKING_BRANCH=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null)

    if [ -z "$TRACKING_BRANCH" ]; then
        echo "目前分支沒有追蹤的遠端分支。"
        echo "正在嘗試設定本地 'master' 分支去追蹤 'origin/main'..."
        git branch --set-upstream-to=origin/main master
        if [ $? -ne 0 ]; then
            echo "設定追蹤分支失敗。請手動處理。"
            echo "您可以嘗試手動執行: git branch --set-upstream-to=origin/<branch> master"
            echo "或者直接執行: git pull origin main"
            return 1 # Return an error code
        else
            echo "成功設定追蹤 origin/main。"
        fi
    fi

    # 現在執行 git pull
    echo "正在執行 git pull..."
    git pull
    if [ $? -ne 0 ]; then
        echo "git pull 執行失敗。"
    else
        echo "成功從遠端拉取最新變更。"
    fi
    echo "--- 拉取功能執行完畢 ---"
}

# Main script logic
while true; do
    show_menu
    case $choice in
        1)
            original_git_operations
            ;;
        2)
            pull_from_remote
            ;;
        q)
            echo "正在退出..."
            break
            ;;
        *)
            echo "無效的選項，請重新輸入。"
            ;;
    esac
    echo "" # Add a newline for better readability
done
