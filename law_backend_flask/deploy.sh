#!/bin/bash

# RAGLEX法律案件管理系统部署脚本
# 用于快速部署整个系统

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 未安装，请先安装 $1"
        exit 1
    fi
}

# 检查必要的依赖
check_dependencies() {
    print_info "检查系统依赖..."
    
    check_command "python3"
    check_command "pip3"
    
    # 检查Python版本
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ $(echo "$python_version < 3.8" | bc -l) -eq 1 ]]; then
        print_error "Python版本需要3.8或更高，当前版本: $python_version"
        exit 1
    fi
    
    print_success "系统依赖检查完成"
}

# 安装Python依赖
install_python_deps() {
    print_info "安装Python依赖..."
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt 文件不存在"
        exit 1
    fi
    
    # 创建虚拟环境（可选）
    if [ "$1" = "--venv" ]; then
        print_info "创建虚拟环境..."
        python3 -m venv venv
        source venv/bin/activate
        print_success "虚拟环境已激活"
    fi
    
    pip3 install -r requirements.txt
    print_success "Python依赖安装完成"
}

# 检查并启动MySQL
setup_mysql() {
    print_info "设置MySQL数据库..."
    
    # 检查MySQL是否运行
    if ! pgrep -x "mysqld" > /dev/null; then
        print_warning "MySQL未运行，尝试启动..."
        
        # 尝试不同的启动方式
        if command -v systemctl &> /dev/null; then
            sudo systemctl start mysql
        elif command -v service &> /dev/null; then
            sudo service mysql start
        else
            print_error "无法启动MySQL，请手动启动MySQL服务"
            exit 1
        fi
        
        sleep 3
        
        if ! pgrep -x "mysqld" > /dev/null; then
            print_error "MySQL启动失败"
            exit 1
        fi
    fi
    
    print_success "MySQL服务正在运行"
    
    # 创建数据库（如果不存在）
    print_info "创建数据库..."
    mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS raglex_law CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || {
        print_warning "无法以root用户连接MySQL，请手动创建数据库 'raglex_law'"
    }
}

# 检查并启动MinIO
setup_minio() {
    print_info "设置MinIO对象存储..."
    
    # 检查MinIO是否运行
    if ! pgrep -f "minio" > /dev/null; then
        print_warning "MinIO未运行"
        
        # 检查是否安装了MinIO
        if ! command -v minio &> /dev/null; then
            print_info "MinIO未安装，正在下载..."
            
            # 下载MinIO
            wget https://dl.min.io/server/minio/release/linux-amd64/minio -O /tmp/minio
            chmod +x /tmp/minio
            sudo mv /tmp/minio /usr/local/bin/
            
            print_success "MinIO安装完成"
        fi
        
        # 创建MinIO数据目录
        mkdir -p ./minio-data
        
        print_info "启动MinIO服务..."
        nohup minio server ./minio-data --console-address ":9001" > minio.log 2>&1 &
        
        sleep 3
        
        if ! pgrep -f "minio" > /dev/null; then
            print_error "MinIO启动失败，请检查 minio.log"
            exit 1
        fi
        
        print_success "MinIO服务已启动"
        print_info "MinIO控制台: http://localhost:9001"
        print_info "默认用户名/密码: minioadmin/minioadmin"
    else
        print_success "MinIO服务正在运行"
    fi
}

# 初始化数据库
init_database() {
    print_info "初始化数据库..."
    
    if [ ! -f "init_db.py" ]; then
        print_error "init_db.py 文件不存在"
        exit 1
    fi
    
    python3 init_db.py
    print_success "数据库初始化完成"
}

# 启动Flask应用
start_flask() {
    print_info "启动Flask应用..."
    
    if [ ! -f "run.py" ]; then
        print_error "run.py 文件不存在"
        exit 1
    fi
    
    # 创建必要的目录
    mkdir -p uploads logs data
    
    # 设置环境变量
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    
    print_success "Flask应用启动中..."
    print_info "应用地址: http://localhost:5000"
    print_info "健康检查: http://localhost:5000/health"
    print_info "API文档: 请查看 README.md"
    
    # 启动应用
    python3 run.py
}

# 使用Docker部署
deploy_with_docker() {
    print_info "使用Docker部署..."
    
    check_command "docker"
    check_command "docker-compose"
    
    # 构建并启动服务
    docker-compose up --build -d
    
    print_success "Docker服务已启动"
    print_info "等待服务初始化..."
    sleep 10
    
    # 初始化数据库
    print_info "初始化数据库..."
    docker-compose exec flask_app python init_db.py
    
    print_success "部署完成！"
    print_info "应用地址: http://localhost:5000"
    print_info "MinIO控制台: http://localhost:9001"
}

# 运行测试
run_tests() {
    print_info "运行API测试..."
    
    if [ ! -f "test_api.py" ]; then
        print_error "test_api.py 文件不存在"
        exit 1
    fi
    
    # 等待服务启动
    sleep 5
    
    python3 test_api.py
}

# 显示帮助信息
show_help() {
    echo "RAGLEX法律案件管理系统部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --help, -h          显示此帮助信息"
    echo "  --check-deps        仅检查系统依赖"
    echo "  --install-deps      安装Python依赖"
    echo "  --venv              使用虚拟环境安装依赖"
    echo "  --setup-mysql       设置MySQL数据库"
    echo "  --setup-minio       设置MinIO对象存储"
    echo "  --init-db           初始化数据库"
    echo "  --start             启动Flask应用"
    echo "  --docker            使用Docker部署"
    echo "  --test              运行API测试"
    echo "  --full              完整部署（不使用Docker）"
    echo ""
    echo "示例:"
    echo "  $0 --full           # 完整部署"
    echo "  $0 --docker         # Docker部署"
    echo "  $0 --test           # 运行测试"
}

# 完整部署
full_deploy() {
    print_info "开始完整部署..."
    
    check_dependencies
    install_python_deps
    setup_mysql
    setup_minio
    init_database
    
    print_success "部署完成！"
    print_info "现在可以运行: $0 --start 来启动应用"
    print_info "或者运行: $0 --test 来测试API"
}

# 主函数
main() {
    case "$1" in
        --help|-h)
            show_help
            ;;
        --check-deps)
            check_dependencies
            ;;
        --install-deps)
            install_python_deps $2
            ;;
        --setup-mysql)
            setup_mysql
            ;;
        --setup-minio)
            setup_minio
            ;;
        --init-db)
            init_database
            ;;
        --start)
            start_flask
            ;;
        --docker)
            deploy_with_docker
            ;;
        --test)
            run_tests
            ;;
        --full)
            full_deploy
            ;;
        "")
            show_help
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
}

# 检查是否在正确的目录
if [ ! -f "app.py" ] || [ ! -f "config.py" ]; then
    print_error "请在项目根目录运行此脚本"
    exit 1
fi

# 运行主函数
main "$@"