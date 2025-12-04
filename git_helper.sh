#!/bin/bash

# Function to select a project subdirectory
select_project_directory() {
    echo "正在偵測專案子目錄..."
    
    # Find all non-hidden directories in the current path and store them in an array
    mapfile -t subdirs < <(find . -maxdepth 1 -mindepth 1 -type d ! -name '.*' | sed 's|^\./||' | sort)

    # Check if any subdirectories were found
    if [ ${#subdirs[@]} -eq 0 ]; then
        echo "未偵測到任何子目錄。將在當前目錄 ($PWD) 執行操作。"
        return
    fi

    echo "請選擇要操作的專案目錄："
    
    # Print a numbered list of directories
    for i in "${!subdirs[@]}"; do
        printf "  %d) %s\n" "$((i+1))" "${subdirs[$i]}"
    done
    
    # Prompt the user for their choice
    read -p "請輸入選項編號: " choice

    # Validate the input
    if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt "${#subdirs[@]}" ]; then
        echo "無效的選項。請輸入 1 到 ${#subdirs[@]} 之間的數字。"
        exit 1
    fi
    
    # Get the selected directory
    selected_dir="${subdirs[$((choice-1))]}"
    echo "已選擇專案: $selected_dir"
    
    # Change into the selected directory
    cd "$selected_dir" || exit
}

# Function to create a default .gitignore if it doesn't exist
create_gitignore_if_needed() {
    if [ ! -f .gitignore ]; then
        echo "找不到 .gitignore 檔案，正在為 Python 專案建立預設檔案。"
        cat <<EOL > .gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# PyInstaller
#  Usually these files are written by a python script from a template
#  before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyderworkspace

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Jupyter Notebook
.ipynb_checkpoints

# IDE settings
.idea/
.vscode/
*.swp
*~
EOL
    fi
}

# Function to move YAML files to .github/workflows
move_yaml_files() {
    # Check if we are in a git repository before proceeding
    if [ ! -d .git ]; then
        return
    fi
    
    if [ -d .github/workflows ]; then
        echo ".github/workflows 目錄已存在。"
    else
        echo "正在建立 .github/workflows 目錄。"
        mkdir -p .github/workflows
    fi

    # Check if there are any .yml or .yaml files in the root directory
    if ls *.yml *.yaml 1> /dev/null 2>&1; then
        echo "正在將根目錄的 YAML 檔案移動到 .github/workflows/"
        # Use find to handle cases where no files of a certain extension exist
        find . -maxdepth 1 -name "*.yml" -exec mv {} .github/workflows/ \;
        find . -maxdepth 1 -name "*.yaml" -exec mv {} .github/workflows/ \;
    else
        echo "根目錄中找不到 YAML 檔案。"
    fi
}

# Function to set up git remote if it doesn't exist
setup_git_repo() {
    # 1. Initialize git if not already done
    if [ ! -d .git ]; then
        echo "正在初始化 Git 儲存庫..."
        git init
    fi

    # 2. Check for remote 'origin' and add if it's missing
    if ! git remote -v | grep -q "origin"; then
        echo "找不到遠端儲存庫 'origin'。"
        read -p "請輸入您的 GitHub 使用者名稱: " github_username
        if [ -z "$github_username" ]; then
            echo "GitHub 使用者名稱不能為空。正在中止操作。"
            exit 1
        fi
        
        # The script assumes the directory name is the repo name
        repo_name=$(basename "$PWD")
        git_url="https://github.com/$github_username/$repo_name.git"
        
        echo "--------------------------------------------------"
        echo "腳本將新增以下遠端儲存庫 URL："
        echo "$git_url"
        echo "請確認此 URL 是否正確 (這需要您的目錄名稱 '$repo_name' 與 GitHub 上的儲存庫名稱一致)。"
        echo "--------------------------------------------------"
        read -p "是否正確？ (y/n): " confirm
        
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            echo "操作已中止。請手動設定遠端儲存庫：git remote add origin <YOUR_URL>"
            exit 1
        fi
        
        git remote add origin "$git_url"
        echo "已新增遠端 'origin': $git_url"
    fi
}

# Function to verify the push was successful
verify_push() {
    local branch_name=$1
    echo "正在驗證遠端分支 '$branch_name' 是否已成功更新..."
    
    # Allow some time for the remote to update
    sleep 2

    # Get local and remote commit hashes
    local_hash=$(git rev-parse HEAD)
    remote_hash=$(git ls-remote origin -h "refs/heads/$branch_name" | awk '{print $1}')

    if [ -z "$remote_hash" ]; then
        echo "警告：無法從遠端获取 '$branch_name' 分支的資訊。可能分支是新的，或者有延遲。"
        echo "請手動在 GitHub 上檢查是否推送成功。"
        return
    fi
    
    if [ "$local_hash" == "$remote_hash" ]; then
        echo "✅ 驗證成功：遠端分支的最新 commit 與本地一致。"
        echo "程式碼已成功推送到 GitHub！"
    else
        echo "❌ 錯誤：遠端分支的 commit ($remote_hash) 與本地 ($local_hash) 不匹配。"
        echo "推送可能失敗或未完全更新。請檢查您的網路連線並重試。"
        exit 1
    fi
}

# --- Main Script ---

# 1. Select the project directory to work on
select_project_directory

# 2. Setup repository (init and remote)
setup_git_repo

# 3. Create supporting files if needed
create_gitignore_if_needed
move_yaml_files

# 4. Add all changes
git add .

# 5. Commit with a message
read -p "請輸入提交訊息 (commit message): " commit_message
if [ -z "$commit_message" ]; then
    commit_message="Update project files" # Default commit message
fi
git commit -m "$commit_message"

# 6. Push to the remote repository
current_branch=$(git rev-parse --abbrev-ref HEAD)
read -p "請輸入要推送的分支名稱 (預設為: $current_branch): " branch_name
if [ -z "$branch_name" ]; then
    branch_name=$current_branch
fi
git push origin "$branch_name"

# 7. Verify the push
verify_push "$branch_name"
