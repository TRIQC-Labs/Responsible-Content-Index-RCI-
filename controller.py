from module_exclusionary import run_exclusionary_analysis
from module_misinformation import run_misinformation_analysis
from module_bias import run_bias_analysis

def evaluate_text(text):
    exclusionary_result = run_exclusionary_analysis(text)
    misinformation_result = run_misinformation_analysis(text)
    bias_result = run_bias_analysis(text)

    final_output = {
        "input_text": text,
        "results": {
            "exclusionary_language": exclusionary_result,
            "misinformation_risk": misinformation_result,
            "bias_and_fairness": bias_result
        }
    }
    return final_output

if __name__ == "__main__":
    user_text = input("Enter text to evaluate: ")
    result = evaluate_text(user_text)
    print(result)