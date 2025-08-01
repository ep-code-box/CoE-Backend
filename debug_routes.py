#!/usr/bin/env python3

import sys
sys.path.append('/app')

from api.chat_api import router

print("Chat API Router endpoints:")
for route in router.routes:
    print(f"  {route.methods} {route.path}")
    if hasattr(route, 'endpoint'):
        print(f"    -> {route.endpoint.__name__}")