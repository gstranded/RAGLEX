#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建测试对话数据
"""

import os
import sys
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User, Conversation, Message

def create_test_conversations():
    """创建测试对话数据"""
    app = create_app('development')
    
    with app.app_context():
        try:
            # 获取或创建测试用户
            user = User.query.filter_by(username='testuser').first()
            if not user:
                user = User(
                    username='testuser',
                    email='test@example.com',
                    real_name='测试用户',
                    is_active=True
                )
                user.set_password('test123')
                db.session.add(user)
                db.session.commit()
            
            # 创建测试对话1
            conv1 = Conversation(
                user_id=user.id,
                title='我是傻逼',
                created_at=datetime.utcnow() - timedelta(days=2),
                updated_at=datetime.utcnow() - timedelta(days=2)
            )
            db.session.add(conv1)
            db.session.flush()  # 获取ID
            
            # 为对话1添加消息
            messages1 = [
                Message(
                    conversation_id=conv1.id,
                    role='user',
                    content='你好，我想咨询一个法律问题',
                    created_at=datetime.utcnow() - timedelta(days=2, hours=1)
                ),
                Message(
                    conversation_id=conv1.id,
                    role='assistant',
                    content='您好！我是法律助手，很高兴为您提供法律咨询服务。请详细描述您遇到的法律问题，我会尽力为您解答。',
                    created_at=datetime.utcnow() - timedelta(days=2, hours=1, minutes=1)
                ),
                Message(
                    conversation_id=conv1.id,
                    role='user',
                    content='我想了解一下劳动合同的相关法律规定',
                    created_at=datetime.utcnow() - timedelta(days=2, hours=1, minutes=2)
                ),
                Message(
                    conversation_id=conv1.id,
                    role='assistant',
                    content='劳动合同是劳动者与用人单位确立劳动关系、明确双方权利和义务的协议。根据《劳动合同法》的规定，劳动合同应当具备以下条款：\n\n1. 用人单位的名称、住所和法定代表人或者主要负责人\n2. 劳动者的姓名、住址和居民身份证或者其他有效身份证件号码\n3. 劳动合同期限\n4. 工作内容和工作地点\n5. 工作时间和休息休假\n6. 劳动报酬\n7. 社会保险\n8. 劳动保护、劳动条件和职业危害防护\n\n您具体想了解劳动合同的哪个方面呢？',
                    created_at=datetime.utcnow() - timedelta(days=2, hours=1, minutes=3)
                )
            ]
            
            for msg in messages1:
                db.session.add(msg)
            
            # 创建测试对话2
            conv2 = Conversation(
                user_id=user.id,
                title='正在加载中...',
                created_at=datetime.utcnow() - timedelta(days=1),
                updated_at=datetime.utcnow() - timedelta(days=1)
            )
            db.session.add(conv2)
            db.session.flush()
            
            # 为对话2添加消息
            messages2 = [
                Message(
                    conversation_id=conv2.id,
                    role='user',
                    content='房屋租赁合同纠纷怎么处理？',
                    created_at=datetime.utcnow() - timedelta(days=1, hours=2)
                ),
                Message(
                    conversation_id=conv2.id,
                    role='assistant',
                    content='房屋租赁合同纠纷的处理方式主要有以下几种：\n\n1. **协商解决**：双方当事人可以就争议事项进行协商，达成一致意见。\n\n2. **调解**：可以向人民调解委员会、房地产管理部门或者消费者协会申请调解。\n\n3. **仲裁**：如果合同中约定了仲裁条款，可以向仲裁机构申请仲裁。\n\n4. **诉讼**：向人民法院提起民事诉讼。\n\n常见的租赁纠纷类型包括：\n- 租金支付纠纷\n- 房屋维修责任纠纷\n- 押金退还纠纷\n- 提前解约纠纷\n\n您遇到的是哪种类型的纠纷呢？',
                    created_at=datetime.utcnow() - timedelta(days=1, hours=2, minutes=1)
                )
            ]
            
            for msg in messages2:
                db.session.add(msg)
            
            # 创建测试对话3（空对话）
            conv3 = Conversation(
                user_id=user.id,
                title='新对话',
                created_at=datetime.utcnow() - timedelta(hours=3),
                updated_at=datetime.utcnow() - timedelta(hours=3)
            )
            db.session.add(conv3)
            
            # 提交所有更改
            db.session.commit()
            
            print("测试对话数据创建成功！")
            print(f"用户ID: {user.id}")
            print(f"对话1 ID: {conv1.id} - {conv1.title}")
            print(f"对话2 ID: {conv2.id} - {conv2.title}")
            print(f"对话3 ID: {conv3.id} - {conv3.title}")
            
        except Exception as e:
            db.session.rollback()
            print(f"创建测试数据失败: {str(e)}")
            raise

if __name__ == '__main__':
    create_test_conversations()