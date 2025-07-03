import multiprocessing

# 服务器套接字
bind = '0.0.0.0:5000'

# 工作进程数
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'gevent'

# 日志配置
accesslog = '/app/logs/gunicorn_access.log'
errorlog = '/app/logs/gunicorn_error.log'
loglevel = 'info'

# 进程名
proc_name = 'raglex_gunicorn'