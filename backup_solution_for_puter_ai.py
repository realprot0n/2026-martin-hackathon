from puter import ChatCompletion

# Basic completion
response = ChatCompletion.create(
    messages=[{"role": "user", "content": "how many usages do i have left"}],
    model="gpt-4o-mini",
    driver="openai-completion",
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0eXBlIjoiZ3VpIiwidmVyc2lvbiI6IjAuMC4wIiwidXVpZCI6ImVhZDI3OTg0LWI2OTgtNGI1OC05ODgyLWRlMWMyMTkzZjlkOSIsInVzZXJfdWlkIjoiMzk3OWFhZDYtNGUzNS00Y2VhLTlmODUtMjgxZDJkNGI0YWFmIiwiaWF0IjoxNzc3MTM1MzM2fQ.yqKnRwuht-MagwnRdv4-Wz4UgdVpfI7Ge_w7DJMQ3kw" # put api key from puter.com here please
)

print(response['result']['message']['content'])