import os
import sys
import time
from main import MainEngine


def typing_print(text):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.01)  # faster + smoother
    print()


def terminal_interface():
    main = MainEngine()

    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 60)
    print("🚀 DEVDOCS AGENTIC RAG v2.0 (Local & Secure)")
    print("=" * 60)

    doc_path = input("📂 Enter docs folder path (default: './docs'): ") or "docs"

    print(f"\n🔍 Indexing documentation at '{doc_path}'...")

    if main.load_local_context(doc_path):
        print("✅ Hybrid Index Ready (Vector + BM25)")
    else:
        print("⚠️ Warning: No PDF documents found. System is in zero-shot mode.")

    print("\n💡 Type 'exit' to quit.")

    while True:
        query = input("\n👤 USER > ")

        if query.lower() in ["exit", "quit"]:
            print("👋 Shutting down...")
            break

        print("⚙️ AGENT > Thinking...", end="\r", flush=True)

        result = main.query(query)

        print(" " * 40, end="\r")  # clear line

        print(f"🤖 AGENT ({result['latency']:.2f}s) >")
        print("-" * 40)

        typing_print(result["answer"])

        if result.get("sources"):
            print("\n📚 REFERENCED SOURCES:")
            for s in result["sources"]:
                print(f" • {s}")

        print("-" * 40)


if __name__ == "__main__":
    try:
        terminal_interface()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")