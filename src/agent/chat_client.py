#!/usr/bin/env python3
"""
Simple command-line chat client for the LLM Agent API.
"""

import argparse
import json
import requests
import uuid
import sys

def parse_arguments():
    parser = argparse.ArgumentParser(description="Command-line client for the LLM Agent API")
    parser.add_argument(
        "--profile", "-p",
        default="default",
        help="Agent profile to use (default: default)"
    )
    parser.add_argument(
        "--host",
        default="http://localhost:8000",
        help="API host URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--session", "-s",
        default=None,
        help="Session ID for conversation continuity (default: auto-generated)"
    )
    return parser.parse_args()

def main():
    args = parse_arguments()
    base_url = args.host
    profile = args.profile
    session_id = args.session or str(uuid.uuid4())
    
    print(f"Chatting with the {profile} agent (session: {session_id})")
    print("Type 'exit' or 'quit' to end the conversation.\n")
    
    while True:
        # Get user input
        try:
            user_input = input("\nYou: ")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
            
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break
            
        if not user_input.strip():
            continue
            
        # Send message to API
        try:
            response = requests.post(
                f"{base_url}/chat",
                json={
                    "text": user_input,
                    "profile_name": profile,
                    "session_id": session_id
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"\nAgent: {data['response']}")
                # Update session ID if it was auto-generated
                session_id = data["session_id"]
            else:
                print(f"\nError: API returned status code {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.RequestException as e:
            print(f"\nError connecting to API: {e}")
            print("Make sure the API server is running.")

if __name__ == "__main__":
    main()