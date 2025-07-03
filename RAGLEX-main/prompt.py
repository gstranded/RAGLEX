# coding: utf-8
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser

# law_prompt_template1 = """你是一个专业的律师，请你结合以下内容回答问题:
# {law_context}

# {web_context}

# 问题: {question}
# """
law_prompt_template = """你是一个专业的律师，请你结合以下内容回答问题:
{law_context}


问题: {question}
"""

# LAW_PROMPT1 = PromptTemplate(
#     template=law_prompt_template, input_variables=["law_context", "web_context", "question"]
# )


LAW_PROMPT = PromptTemplate(
    template=law_prompt_template, input_variables=["law_context", "question"]
)

####添加历史记录#########
law_prompt_template_history = """  
你是一名专业律师，请严格按以下要求回答问题：  

【回答规则】  
1. 必须基于提供的法律条文，禁止编造  
2. 引用格式：`《法律名称》第XX条`（如：根据《刑法》第264条...）  
3. 若无相关法条，明确告知无法回答 

【历史对话记录】  
{chat_history}  

【相关法律条文】  
{law_context}  

【用户问题】  
{question}  

【正式回答】  
"""  
LAW_PROMPT_HISTORY = PromptTemplate(  
    template=law_prompt_template_history,  
    input_variables=["chat_history", "law_context", "question"]  
)  


# CHECK_LAW_PROMPT的核心作用就是将用户输入注入到模板的{question}位置
check_law_prompt_template = """你是一名律师，请判断下面问题是否和法律相关，相关请回答YES，不相关请回答NO，不允许其它任何形式的输出，不允许在答案中添加编造成分。
问题: {question}
"""

CHECK_LAW_PROMPT = PromptTemplate(
    template=check_law_prompt_template, input_variables=["question"]
)

hypo_questions_prompt_template = """生成 5 个假设问题的列表，以下文档可用于回答这些问题:\n\n{context}"""

HYPO_QUESTION_PROMPT = PromptTemplate(
    template=hypo_questions_prompt_template, input_variables=["context"]
)

# 多查询检索
multi_query_prompt_template = """您是 AI 语言模型助手。您的任务是生成给定用户问题的3个不同版本，以从矢量数据库中检索相关文档。通过对用户问题生成多个视角，您的目标是帮助用户克服基于距离的相似性搜索的一些限制。每个问题占单独一行，不要添加任何额外格式，不要给出多余的回答。问题：{question}""" # noqa
MULTI_QUERY_PROMPT_TEMPLATE = PromptTemplate(
    template=multi_query_prompt_template, input_variables=["question"]
)

formal_question_prompt_template =  """你是一名法律文书助理，请根据以下要求转换问题：
    
    **输入要求**：
    - 原始问题可能包含口语化、模糊或不规范表达
    - 需要符合《中华人民共和国立法法》对法律条文表述的要求
    
    **转换规则**：
    1. 使用完整的主谓宾结构，例如将“打人判几年？”改为“故意伤害他人身体的，应承担何种刑事责任？”
    2. 明确法律主体，如将“公司欠钱不还怎么办？”改为“企业法人未履行债务清偿义务时，债权人可采取哪些法律救济途径？”
    3. 采用法言法语替换口语词汇，例如：
       - "偷东西" -> "盗窃公私财物"
       - "离婚财产" -> "婚姻关系解除后的共同财产分割"
    4. 补充隐含法律要件，如将“酒驾怎么处理？”改为“驾驶机动车时血液酒精含量达到80mg/100ml以上的，应如何依法处置？”
    
    原始问题：{question}
    
    正式法律问题："""
FORMAL_QUESTION_PROMPT = PromptTemplate(
    template=formal_question_prompt_template,input_variables = ["question"]
)


check_intent_prompt_template = """  
# 法律意图识别分类器
**主任务**：判断当前问题是否涉及法律咨询或相关领域，仅返回小写单词law或other
## 判断标准
1. 返回"law"的情形：
- 包含法律术语（如诉讼、合同、刑事责任等）
- 涉及权利义务关系的确认
- 咨询法律程序或维权方式
- 需要法律建议或案例参考
- 法律相关咨询

2. 返回"other"的情形：
- 日常闲聊或通用问题
- 其他专业领域（医疗、金融、IT技术等）
- 与法律无关的个人事务咨询

## 强制要求
1. 禁止任何解释说明
2. 禁止使用标点符号
3. 必须小写字母输出

[当前问题]
{question}

## 识别判断
"""  
CHECK_INTENT_PROMPT = PromptTemplate(  
    template=check_intent_prompt_template,  
    input_variables=["question"]  
)  


FRIENDLY_REJECTION_PROMPT_template = """
[用户问题]
{question}

[对话延续规则]  
1️⃣ **情感共鸣**：先回应原始问题的情感价值  
2️⃣ **场景关联**：挖掘该话题下的潜在法律需求
3️⃣ **开放引导**：给用户提供咨询方向

[示例指令]  
用户：最近想辞职去旅游  
→ "放松身心确实很重要呢！(😊) 在规划旅程时，是否需要了解：  
• 离职期间的劳动权益保障  
• 旅游合同中的消费者保护条款  
• 旅途意外伤害的法律责任划分"  


用户：推荐周末活动  
→ "休闲活动能缓解压力呢~(🌿) 如果涉及：  
• 活动场地的安全责任  
• 预付卡消费纠纷  
• 人身意外保险索赔  
这些法律知识可能会帮到您！
"""
FRIENDLY_REJECTION_PROMPT=PromptTemplate(  
    template=FRIENDLY_REJECTION_PROMPT_template,  
    input_variables=["question"]  
)  

pre_question_prompt_template = """你是问题补全助手。任务：将用户当前输入补全为完整独立的问题。

【严格要求】
1. 只输出一个完整的问题句子
2. 不要任何解释、说明、前缀、后缀
3. 不要输出多个问题
4. 不要输出答案或建议

【处理逻辑】
- 如果当前输入是完整问题 → 直接输出原问题
- 如果当前输入需要补全 → 基于历史用户问题补全
- 如果包含指代词（这、那、它等）→ 替换为具体内容
- 如果是延续性表达（"还有呢"、"怎么办"等）→ 补全为完整问题

【输入】
历史用户问题：{chat_history}
当前用户输入：{question}

【输出】
补全后的问题："""  

PRE_QUESTION_PROMPT = PromptTemplate(  
    template=pre_question_prompt_template,  
    input_variables=["chat_history", "question"]
)

# 来源摘要生成模板
SOURCE_SUMMARY_PROMPT_TEMPLATE = """你是一名严谨的法律助理。你的任务是根据下面提供的"相关法律条文"和"相关案例"，为一份法律咨询回答生成格式化、简洁的"引用来源"部分。

【严格规则】
1. **只输出"引用来源"部分**，不要包含任何其他评论或正文回答。
2. **格式必须完全遵循**：以`---`分隔符开始，然后是`**法律条文依据：**`和`**案例依据：**`。
3. 如果只提供了法律条文，则只输出"法律条文依据"部分。
4. 如果只提供了案例，则只输出"案例依据"部分。
5. 如果都没有提供，则输出空字符串。
6. **对法律条文，必须明确标注法律名称和条文号**，格式为："《法律名称》第X条规定：[条文内容]"。如果无法确定具体条文号，至少要标注法律名称。
7. 对案例，用一句话总结"谁/因何事/被怎样处理"，风格需简洁、客观。
8. **法律条文依据和案例依据要有明显的格式区分**，使用不同的标识符和缩进。

【输入信息】

相关法律条文：
{law_context}

相关案例：
{case_context}

【你的输出】"""

SOURCE_SUMMARY_PROMPT = PromptTemplate(
    template=SOURCE_SUMMARY_PROMPT_TEMPLATE,
    input_variables=["law_context", "case_context"]
)

# 新增：案例深度加工和结构化的Prompt模板
TRANSFORM_AND_STRUCTURE_PROMPT_TEMPLATE = """你是一位资深的法律文书专家和书记员。
你的任务是读取一份原始、格式不一的法律案例文本，然后将其**深度加工、重新组织并结构化**为一份内容完整、格式清晰标准的JSON对象。

【核心指令】
- **综合全文**：你需要阅读并理解整个原始文本，而不仅仅是做简单的信息匹配。
- **归纳与重写**：对于"基本案情"和"裁判理由"等段落，你需要用自己的语言进行归纳、总结和重新叙述，而不是直接复制原文。
- **提取与生成**：对于"关键词"、"案例编号"等字段，你需要从文本中精确提取。
- **处理缺失信息**：如果原文中明确缺少某个信息（如案例编号、判决日期），请将对应字段的值设为 `null`。

【字段处理详解】
- `标题`: 直接提取或生成最核心的案件标题。
- `关键词`: 提取或生成最能概括案件核心特征的关键词列表。
- `案例类型`: 识别案件属于哪个领域，如"刑事"、"民事"、"执行/破产"等。
- `案例编号`: 精确提取官方案件编号，若无则为 `null`。
- `基本案情`: **【重点】** 综合全文，用客观、中立的语言，**从头完整地叙述**案件的背景、起因、经过、各方的主要诉求和纠纷点。这是最重要的部分，需要详细、完整。
- `裁判理由`: **【重点】** 详细总结法院做出判决的核心逻辑、原因和考量。解释"为什么这么判"。
- `裁判要旨`: **【重点】** 从"裁判理由"和全文中，提炼出最高度概括、可供其他案件参考的法律原则或观点。这是"判决的精髓"。
- `法律条文`: 列出所有在案件中明确提到的法律条文。
- `法院`: 提取审理该案件的法院全称。
- `判决日期`: 提取判决或裁定的具体日期。

【原始案例文本】
{text}

【输出要求】
你必须严格按照下面定义的JSON格式输出，不要有任何额外的解释或文本。
{format_instructions}
"""

# 注意：这里需要导入IdealCaseStructure
# from receive_data import IdealCaseStructure  # 移除循环导入

# TRANSFORM_AND_STRUCTURE_PROMPT将在receive_data.py中动态创建以避免循环导入
# TRANSFORM_AND_STRUCTURE_PROMPT = PromptTemplate(
#     template=TRANSFORM_AND_STRUCTURE_PROMPT_TEMPLATE,
#     input_variables=["text"],
#     partial_variables={"format_instructions": PydanticOutputParser(pydantic_object=IdealCaseStructure).get_format_instructions()}
# )