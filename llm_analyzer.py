import pandas as pd
import os # For path manipulation if needed later, and to get filename
import openai # Added for LLM API call
import json # For parsing plot suggestions

def analyze_data_with_llm(user_request: str, llm_model_name: str, api_key: str, csv_file_paths: list[str]) -> dict:
    """
    Analyzes data from CSV files using a Large Language Model (LLM).

    Args:
        user_request (str): The user's natural language request.
        llm_model_name (str): The name of the LLM model to use (can be empty for default).
        api_key (str): The API key for the LLM.
        csv_file_paths (list[str]): A list of paths to the CSV files containing the data.

    Returns:
        str: A placeholder string indicating where LLM analysis will occur.
             In the future, this will be the LLM's response.
    """
    
    data_frames_as_strings = []
    successfully_read_files = []

    for file_path in csv_file_paths:
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                print(f"Warning: CSV file '{file_path}' is empty and will be skipped.")
                continue 
            
            file_name = os.path.basename(file_path)
            header = f"--- Data from: {file_name} ---\n"
            df_string = df.to_csv(index=False)
            
            data_frames_as_strings.append(header + df_string)
            successfully_read_files.append(file_path)
            
        except FileNotFoundError:
            print(f"User Info: Data file not found at '{file_path}'. This file will be skipped.")
        except pd.errors.EmptyDataError: # This is often caught by the df.empty check earlier if read succeeds
            print(f"User Info: No data in CSV file '{file_path}'. This file will be skipped.")
        except pd.errors.ParserError:
            print(f"User Info: Could not parse data from CSV file '{file_path}'. It might be corrupted or not a valid CSV. This file will be skipped.")
        except Exception as e:
            print(f"User Info: An unexpected error occurred while reading '{file_path}': {e}. This file will be skipped.")

    if not successfully_read_files: # Changed condition to check if any file was read
        error_message = "No valid data could be loaded from the provided CSV files. Analysis cannot proceed."
        print(f"Error: {error_message}")
        return {"text_analysis": error_message, "plot_suggestion": None}
    
    formatted_data_for_llm = "\n\n".join(data_frames_as_strings)

    # Print the inputs and the prepared data
    print("\n--- LLM Analysis Inputs ---")
    print(f"User Request: {user_request}")
    print(f"LLM Model Name: {llm_model_name if llm_model_name else 'Default (not specified)'}")
    print(f"API Key Received: {'Yes' if api_key else 'No'}") # Don't print the key itself
    print(f"Successfully Processed CSV File Paths: {successfully_read_files}")
    print("\n--- Formatted Data for LLM ---")
    print(formatted_data_for_llm)
    print("--- End of Formatted Data ---")

    try:
        openai.api_key = api_key
        
        # Default model if not provided
        model_to_use = llm_model_name if llm_model_name else "gpt-3.5-turbo"
        print(f"Using LLM Model: {model_to_use}")

        messages = [
            {"role": "system", "content": "You are a helpful assistant that analyzes scientific data from tree ring studies. The user will provide data from one or more CSV files and a request for analysis."},
            {"role": "user", "content": f"Here is the data:\n{formatted_data_for_llm}"},
            {"role": "user", "content": user_request}
        ]

        print("\nAttempting to call OpenAI API...")
        
        # Note: The OpenAI library version might affect the exact client/method used.
        # Assuming a recent version where `openai.ChatCompletion.create` is standard.
        # For openai >= 1.0.0, the client instantiation is different:
        # from openai import OpenAI
        # client = OpenAI(api_key=api_key)
        # response = client.chat.completions.create(model=model_to_use, messages=messages)
        # For older versions (like 0.28), openai.ChatCompletion.create is correct.
        # The installed version is 1.81.0, so the new client syntax should be used.
        
        client = openai.OpenAI(api_key=api_key) # Corrected client initialization
        response = client.chat.completions.create(
            model=model_to_use,
            messages=messages
        )
        
        llm_text_response = response.choices[0].message.content
        print("LLM Response Received.")

        plot_suggestion_info = None
        text_analysis_part = llm_text_response

        # Search for plot suggestion
        if "PLOT_SUGGESTION:" in llm_text_response:
            lines = llm_text_response.splitlines()
            plot_suggestion_str = None
            temp_text_analysis_lines = []

            for line in lines:
                if line.startswith("PLOT_SUGGESTION:"):
                    plot_suggestion_str = line.replace("PLOT_SUGGESTION:", "").strip()
                else:
                    temp_text_analysis_lines.append(line)
            
            text_analysis_part = "\n".join(temp_text_analysis_lines).strip()

            if plot_suggestion_str:
                try:
                    # Attempt to parse as JSON
                    plot_suggestion_info = json.loads(plot_suggestion_str)
                    print(f"Parsed PLOT_SUGGESTION: {plot_suggestion_info}")
                except json.JSONDecodeError as je:
                    print(f"Error decoding PLOT_SUGGESTION JSON: {je}")
                    # Basic string parsing as fallback (optional, or just fail parsing)
                    # For this task, if JSON fails, we can set plot_suggestion_info to None or a simple error dict
                    plot_suggestion_info = {"error": "Failed to parse plot suggestion JSON", "raw": plot_suggestion_str}
        
        return {"text_analysis": text_analysis_part, "plot_suggestion": plot_suggestion_info}

    except openai.AuthenticationError as e:
        error_message = f"OpenAI API Authentication Error: Invalid API key provided. Please check your API key. (Details: {e})"
        print(error_message)
        return {"text_analysis": error_message, "plot_suggestion": None}
    except openai.RateLimitError as e:
        error_message = f"OpenAI API Rate Limit Exceeded: The server is receiving too many requests. Please wait and try again later. (Details: {e})"
        print(error_message)
        return {"text_analysis": error_message, "plot_suggestion": None}
    except openai.APIConnectionError as e:
        error_message = f"OpenAI API Connection Error: Could not connect to OpenAI. Please check your network connection. (Details: {e})"
        print(error_message)
        return {"text_analysis": error_message, "plot_suggestion": None}
    except openai.APIError as e: # Catch generic API errors
        error_message = f"OpenAI API Error: An issue occurred on OpenAI's side. (Details: {e})"
        print(error_message)
        return {"text_analysis": error_message, "plot_suggestion": None}
    except openai.InvalidRequestError as e:
        error_message = f"OpenAI API Invalid Request Error: The request was malformed or invalid. This could be due to an unsupported model name or issues with the input data format. (Details: {e})"
        print(error_message)
        return {"text_analysis": error_message, "plot_suggestion": None}
    except openai.Timeout as e:
        error_message = f"OpenAI API Request Timed Out: The request took too long to complete. Please try again. (Details: {e})"
        print(error_message)
        return {"text_analysis": error_message, "plot_suggestion": None}
    except openai.ServiceUnavailableError as e:
        error_message = f"OpenAI API Service Unavailable: The OpenAI servers are currently unavailable. Please try again later. (Details: {e})"
        print(error_message)
        return {"text_analysis": error_message, "plot_suggestion": None}
    except Exception as e:
        error_message = f"An unexpected error occurred during the LLM API call: {e}. Please check the application logs for more details."
        print(error_message)
        return {"text_analysis": error_message, "plot_suggestion": None}


if __name__ == '__main__':
    # Example Usage (for testing the module directly)
    print("Testing llm_analyzer.py directly...")

    # Create dummy CSV files for testing
    if not os.path.exists("test_data"):
        os.makedirs("test_data")
    
    df1_data = {'col1': [1, 2], 'col2': ['a', 'b']}
    df1 = pd.DataFrame(df1_data)
    df1.to_csv("test_data/dummy1.csv", index=False)

    df2_data = {'temp': [10, 15, 12], 'site': ['X', 'Y', 'X']}
    df2 = pd.DataFrame(df2_data)
    df2.to_csv("test_data/dummy2.csv", index=False)
    
    # Create an empty CSV file
    with open("test_data/empty.csv", 'w') as f:
        pass # Just create the file

    # Test case 1: Valid files
    print("\n--- Test Case 1: Valid files ---")
    paths1 = ["test_data/dummy1.csv", "test_data/dummy2.csv"]
    result1 = analyze_data_with_llm(
        user_request="Summarize trends in col1 and temperature.",
        llm_model_name="gpt-4-mini",
        api_key="dummy_api_key_12345",
        csv_file_paths=paths1
    )
    print(f"Function returned: {result1}") # This will now be a dict
    if result1["plot_suggestion"]:
        print(f"Plot suggestion found: {result1['plot_suggestion']}")

    # Test case 2: Mix of valid, not found, and empty files
    print("\n--- Test Case 2: Mix of valid, not found, and empty files ---")
    paths2 = ["test_data/dummy1.csv", "test_data/non_existent.csv", "test_data/empty.csv"]
    result2 = analyze_data_with_llm(
        user_request="Analyze col2.",
        llm_model_name="", # Test with empty model name
        api_key="another_key_67890",
        csv_file_paths=paths2
    )
    print(f"Function returned: {result2}") # This will now be a dict
    if result2["plot_suggestion"]:
        print(f"Plot suggestion found: {result2['plot_suggestion']}")

    # Test case 3: No valid files
    print("\n--- Test Case 3: No valid files ---")
    paths3 = ["test_data/non_existent_again.csv"]
    result3 = analyze_data_with_llm(
        user_request="This should not find data.",
        llm_model_name="some_model",
        api_key="key_for_no_data",
        csv_file_paths=paths3
    )
    print(f"Function returned: {result3}") # This will now be a dict
    if result3["plot_suggestion"]:
        print(f"Plot suggestion found: {result3['plot_suggestion']}")

    # Test case 4: Mock LLM response with a plot suggestion
    print("\n--- Test Case 4: Mock LLM response with plot suggestion ---")
    # Temporarily mock the openai.OpenAI class and its methods for this test
    original_openai_client = openai.OpenAI
    class MockChoice:
        def __init__(self, content):
            self.message = MockMessage(content)
    class MockMessage:
        def __init__(self, content):
            self.content = content
    class MockCompletions:
        def create(self, model, messages):
            # Simulate an LLM response that includes a plot suggestion
            mock_response_content = (
                "This is the textual analysis part.\n"
                "PLOT_SUGGESTION: {\"type\": \"line\", \"data_file\": \"dummy1.csv\", \"x_column\": \"col1\", \"y_column\": \"col2\", \"title\": \"Dummy Plot 1\"}\n"
                "Some more text after the suggestion."
            )
            return MockChoice(content=mock_response_content)
    class MockOpenAI:
        def __init__(self, api_key):
            self.chat = MockChat()
    class MockChat:
        def __init__(self):
            self.completions = MockCompletions()
            
    openai.OpenAI = MockOpenAI # Override the client

    paths4 = ["test_data/dummy1.csv"] # Ensure dummy1.csv exists from previous tests
    result4 = analyze_data_with_llm(
        user_request="Analyze and suggest a plot for dummy1.csv.",
        llm_model_name="gpt-mock",
        api_key="mock_key",
        csv_file_paths=paths4
    )
    print(f"Function returned: {result4}")
    assert result4["plot_suggestion"] is not None
    assert result4["plot_suggestion"]["type"] == "line"
    assert "textual analysis part" in result4["text_analysis"]
    assert "PLOT_SUGGESTION" not in result4["text_analysis"]
    
    openai.OpenAI = original_openai_client # Restore original client

    # Clean up dummy files
    # print("\nCleaning up test files...")
    # os.remove("test_data/dummy1.csv")
    # os.remove("test_data/dummy2.csv")
    # os.remove("test_data/empty.csv")
    # os.rmdir("test_data")
    # print("Test files cleaned up.")
