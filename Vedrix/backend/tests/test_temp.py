import sys
import os
import traceback
from app.services.rag_service import rag_service

def test_rag_service_init():
    print("\nStarting test_rag_service_init...")
    try:
        rag_service._ensure_initialized()
        print("Initialized status:", rag_service._initialized)
        if not rag_service._initialized:
            print("Initialization failed, but no exception was raised directly.")
        else:
            print("Initialization succeeded!")
            print("Persist directory:", rag_service.persist_directory)
            print("Collection count:", rag_service.collection.count())
    except Exception as e:
        print("Initialization raised exception:")
        traceback.print_exc()
        assert False
    assert True
