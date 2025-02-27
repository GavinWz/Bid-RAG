from nltk.translate.bleu_score import sentence_bleu

text1 = """当单一来源采购方式公示被质疑时，应按照政府采购的相关规定和程序进行处理：

1. **回应质疑**：首先需要对质疑内容进行认真研究，并准备详细的书面答复。如果质疑涉及到具体事实或数据问题，应当提供相应的证据支持。

2. **内部审核**：组织相关部门或人员对采购过程进行全面审查，确保整个流程符合法律法规要求，特别是关于单一来源采购的规定和程序是否合规。

3. **公开澄清**：对于合理的质疑点，在适当范围内进行公开澄清说明。可以通过官方网站、公告栏等方式发布相关信息，增加透明度。

4. **调整采购计划（如有必要）**：根据质疑反馈的结果，如果发现确实存在不符合规定的情况，则需要及时调整采购方案或重新启动招标程序。

5. **记录存档**：将整个处理过程详细记录下来，并妥善保存相关文件资料以备后续查阅和审计使用。

6. **接受监督**：主动接受财政部门、监察机关等相关部门的监督检查，确保采购活动合法合规进行。

7. **加强培训教育**：针对内部工作人员开展政府采购法律法规的学习与培训工作，提高其业务水平及法律意识。

8. **完善制度建设**：总结经验教训，进一步健全和完善本单位的采购管理制度和流程，避免类似问题再次发生。

在整个过程中，保持沟通渠道畅通非常重要，既要积极回应质疑方的意见，也要及时向相关监管机构汇报进展情况。"""

text2 = """单一来源没有质疑、投诉，供应商只能在公示期间提出异议，采购人、采购代理机构收到对采用单一来源采购方式公示的异议后，应当在公示期满后5个工作日内，组织补充论证，论证后认为异议成立的，应当依法采取其他采购方式；论证后认为异议不成立的，应当将异议意见、论证意见与公示情况一并报相关财政部门。采购人、采购代理机构应当将补充论证的结论告知提出异议的供应商、单位或者个人。《政府采购非招标采购方式管理办法》（财政部令第74号）第三十九条　任何供应商、单位或者个人对采用单一来源采购方式公示有异议的，可以在公示期内将书面意见反馈给采购人、采购代理机构，并同时抄送相关财政部门。第四十条采购人、采购代理机构收到对采用单一来源采购方式公示的异议后，应当在公示期满后5个工作日内，组织补充论证，论证后认为异议成立的，应当依法采取其他采购方式；论证后认为异议不成立的，应当将异议意见、论证意见与公示情况一并报相关财政部门。采购人、采购代理机构应当将补充论证的结论告知提出异议的供应商、单位或者个人。"""

def bleu_func():
    # 参考文本（可以有多条参考文本）
    reference = [["the", "cat", "is", "on", "the", "mat"]]

    # 生成文本
    candidate = ["the", "cat", "is", "on", "mat"]

    # 计算 BLEU 分数
    bleu_score = sentence_bleu(reference, candidate)
    print("BLEU 分数:", bleu_score)

def bleu_func1():
    # 参考文本（可以有多条参考文本）
    reference = text2.split()

    # 生成文本
    candidate = text1.split()

    # 计算 BLEU 分数
    bleu_score = sentence_bleu(reference, candidate)
    print("BLEU 分数:", bleu_score)

def rouge_func():
    from rouge import Rouge

    # 参考文本和生成文本
    reference = "the cat is on the mat"
    candidate = "the cat is on the "

    # 初始化 ROUGE 评估器
    rouge = Rouge()

    # 计算 ROUGE 分数
    scores = rouge.get_scores(candidate, reference)

    # 输出结果
    print("ROUGE-1:", scores[0]['rouge-1'])
    print("ROUGE-2:", scores[0]['rouge-2'])
    print("ROUGE-L:", scores[0]['rouge-l'])

if __name__ == "__main__":
    # bleu_func()
    # rouge_func()
    bleu_func1()