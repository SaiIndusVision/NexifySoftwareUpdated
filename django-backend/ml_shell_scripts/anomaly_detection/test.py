import os
import json
import argparse
import requests

import cv2
from anomaly_tester import AnomalyTester


def test(args):
    # create test_runs directory
    results_save_dir = args.results_save_dir + "/test_runs"
    os.makedirs(results_save_dir, exist_ok=True)

    # create timestamp directory
    results_save_dir = results_save_dir + f"/{args.save_result_dir_timestamp}"
    os.makedirs(results_save_dir, exist_ok=True)

    # Set up detector
    try:
        detector = AnomalyTester(model_name=args.model_name, ckpt_path=args.ckpt_path)
    except Exception as e:
        print(json.dumps({"error": f"Model loading failed: {str(e)}"}))
        return

    # Fetch test dataset
    try:
        response = requests.get(args.fetch_testset_url)
        if response.status_code == 200:
            list_img_obj = response.json()
        else:
            print(f"Error: {response.status_code}, {response.text}")

    except Exception as e:
        print(json.dumps({"error": f"Failed to fetch or parse dataset: {str(e)}"}))
        return

    # Infer results on images
    for item in list_img_obj:
        image_path = item.get("image")
        label_id = item.get("label_id")

        base_name = os.path.basename(image_path)

        if not image_path:
            continue

        try:
            result = detector.infer(image_path)
            # result = {
            # "result_image": result_image,
            # "predicted_label": pred_label,
            # "predicted_score": pred_score
            # }
            cv2.imwrite(results_save_dir+f'/{base_name}', result['result_image'])

            del result['result_image']
            result["label_id"] = label_id

            with open(results_save_dir+f'/{os.path.splitext(base_name)[0]}.json', 'w') as file:
                json.dump(result, file, indent=4)

        except Exception as e:
            print('Exception occured during inference {e}')
            pass

    payload = {
        "job_id": "12345",
        "progress" : 100,
        "status":"Done"
    }

    response = requests.post(args.progress_api, json=payload)

    if response.status_code in {200, 201}:
        print("Progress sent successfully")
        return True
    else:
        print(f"Progress send failed. Status code: {response.status_code}, Response: {response.text}")
        return False
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Anomaly Detection Testing Script")

    parser.add_argument("--sku_id", type=int, required=True, help="SKU Id of the testset.")
    parser.add_argument("--version_id", type=str, required=True, help="Version Id of the testset.")
    parser.add_argument("--model_name", type=str, required=True, help="Name of the anomaly detection model to use (e.g., padim, patchcore)")
    parser.add_argument("--ckpt_path", type=str, required=True, help="Path to the model checkpoint file")
    parser.add_argument("--results_save_dir", type=str, required=True, help="Media save path ")
    parser.add_argument("--fetch_testset_url", type=str, required=True, help="URL to fetch the test dataset from") # For fetching dataset for test
    parser.add_argument("--save_result_dir_timestamp", type=str, required=True, help="The directory path where results need to be saved")
    parser.add_argument("--progress_api", type=str, required=True, help="End point url to update training status")

    args = parser.parse_args()
    test(args)
