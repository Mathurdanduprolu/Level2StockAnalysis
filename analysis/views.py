from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .forms import StockImageForm
from .models import StockImage
import openai
import requests
import base64


openai.api_key = 'YOUR_OPENAI_API_KEY'

# Function to encode the image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def upload_image(request):
    if request.method == 'POST':
        form = StockImageForm(request.POST, request.FILES)
        if form.is_valid():
            stock_image = form.save()
            image_path = stock_image.image.path

            # Encode the image to base64
            base64_image = encode_image(image_path)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai.api_key}"
            }

            payload = {
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze the stock level 2 data and provide insights. Output response sould be in the following format. The example give is for stock BNAI. \n\n- **Stock Ticker Symbol:** BNAI\n- **Best Bid:** $7.35 with a size of 895.\n- **Best Ask:** $7.40 with a size of 400.\n\nThe accompanying market depth chart visualizes the bid and ask prices at different size levels, providing a graphical representation of supply and demand for the stock.\n\nFurther detailed bid-ask data provided include:\n- Bid: $7.35, Size: 895\n- Bid: $7.31, Size: 1\n- Bid: $7.30, Size: 500\n- Ask: $7.40, Size: 400\n- Ask: $7.43, Size: 45\n- Ask: $7.44, Size: 615\n\nThe current trading price of BNAI is shown as $7.39 with a significant increase of +186.43%.\n\nInclude information about volatility and spread."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 500
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    stock_image.summary = result['choices'][0]['message']['content']
                else:
                    stock_image.summary = "No summary available."
                stock_image.save()
            else:
                stock_image.summary = "Error in API response."
                print(response.json())
            return redirect(reverse('summary', kwargs={'pk': stock_image.pk}))
    else:
        form = StockImageForm()
    return render(request, 'analysis/upload_image.html', {'form': form})

def summary(request, pk):
    stock_image = get_object_or_404(StockImage, pk=pk)
    if request.method == 'POST':
        question = request.POST.get('question')
        if question:
            image_path = stock_image.image.path
            base64_image = encode_image(image_path)

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai.api_key}"
            }

            payload = {
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Analyze the stock level 2 data and answer {question}"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 300
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    stock_image.questions = (stock_image.questions or "") + "\n\nQ: " + question + "\nA: " + result['choices'][0]['message']['content']
                else:
                    stock_image.questions = (stock_image.questions or "") + "\n\nQ: " + question + "\nA: No answer available."
                stock_image.save()
            else:
                print(response.json())  # Handle error response
    return render(request, 'analysis/summary.html', {'stock_image': stock_image})
