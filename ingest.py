import os
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings


def main():
    """
    'data' 디렉토리의 문서를 로드하여 청크로 분할하고,
    OpenAI 임베딩을 사용하여 Chroma 벡터 데이터베이스에 저장합니다.
    """
    print("🚀 데이터 인덱싱을 시작합니다...")

    # 1. 환경 변수 로드 (OPENAI_API_KEY)
    load_dotenv()

    # 2. 데이터 로드
    # 'data' 디렉토리의 모든 문서를 로드합니다.
    loader = DirectoryLoader('./data/', glob="**/*.md")
    documents = loader.load()
    if not documents:
        print("⚠️ 'data' 디렉터리에서 처리할 문서를 찾을 수 없습니다.")
        return

    # 3. 텍스트 분할
    # 문서를 관리하기 쉬운 작은 청크로 분할합니다.
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)
    print(f"📄 총 {len(documents)}개의 문서를 {len(texts)}개의 청크로 분할했습니다.")

    # 4. 벡터 DB에 저장
    # OpenAI 임베딩 모델을 사용하여 텍스트 청크를 벡터로 변환하고 ChromaDB에 저장합니다.
    # 'db' 디렉터리에 데이터가 영구적으로 저장됩니다.
    Chroma.from_documents(texts, OpenAIEmbeddings(), persist_directory="./db")
    print("✅ 데이터 인덱싱 및 벡터 DB 저장이 완료되었습니다.")

if __name__ == "__main__":
    main()