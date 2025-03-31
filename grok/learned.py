from question_executor import answer_question

# Ask a question
while True:
    print('Ask me anything!')
    query = input()
    if not query or 'bye' in query.lower():
        break
    result = answer_question(query)
    print(result)