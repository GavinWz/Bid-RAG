from PyPDF2 import PdfReader
 
 
# 获取pdf文件内容
def get_pdf_text(pdf):
    text = ""
    pdf_reader = PdfReader(pdf)
    for page in pdf_reader.pages:
        text += page.extract_text()
 
    return text

print(get_pdf_text("/root/rag_project/crawl/table_clean/file_downloads/中标结果-附件/《合肥市产业用地指南》修订/安徽合肥公共资源交易中心网上投诉操作手册-投标人.pdf"))