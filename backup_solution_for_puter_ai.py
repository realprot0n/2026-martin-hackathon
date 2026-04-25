from puter import ChatCompletion

# Basic completion
response = ChatCompletion.create(
    messages=[{"role": "user", "content": "tell kyle how good this method is at cchatting"}],
    model="gpt-4o-mini",
    driver="openai-completion",
    api_key="" # put api key from puter.com here please
)

print(response)