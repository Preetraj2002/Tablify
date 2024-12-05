import cv2
import pytesseract
import csv
import sys

def get_bounding_box(cnt):
    x, y, w, h = cv2.boundingRect(cnt)
    return x, y, w, h

def group_and_sort_contours(contours, y_tolerance=15):
    rows = []
    current_row = []

    # Sort contours by the top-left y-coordinate (y-value of the bounding box)
    contours = sorted(contours, key=lambda cnt: get_bounding_box(cnt)[1])

    prev_y = None

    for cnt in contours:
        x, y, w, h = get_bounding_box(cnt)

        if prev_y is None or abs(y - prev_y) <= y_tolerance:
            current_row.append(cnt)  # Add to the current row if within tolerance
        else:
            # Sort the current row by x-coordinate and add to rows list
            rows.append(sorted(current_row, key=lambda c: get_bounding_box(c)[0]))
            current_row = [cnt]

        prev_y = y

    # Sort and append the last row
    if current_row:
        rows.append(sorted(current_row, key=lambda c: get_bounding_box(c)[0]))

    # Flatten the list of rows into a single list of contours
    sorted_contours = [cnt for row in rows for cnt in row]
    return sorted_contours

def main():
    # Check if at least one argument (the image path) is provided
    if len(sys.argv) < 2:
        print("Usage: python tablify_img.py <image_path> [output_path]")
        sys.exit(1)
    
    # Get the image path (first argument)
    image_path = sys.argv[1]
    
    # If an output path is provided (second argument), use it, otherwise default to 'output.csv'
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'output.csv'
    
    print(f"Processing image: {image_path}")
    print(f"Output CSV will be saved to: {output_path}")

    img = cv2.imread(image_path)

    # Preprocessing the image starts
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Performing OTSU threshold
    ret, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV)

    # cv2.imwrite("gray_image.png", gray)
    # cv2.imwrite("thresholded_image.png", thresh1)

    # Get a Rectangular Kernel
    rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 18))

    # Applying dilation on the threshold image
    dilation = cv2.dilate(thresh1, rect_kernel, iterations = 1)

    # Finding contours
    contours, hierarchy = cv2.findContours(dilation, cv2.RETR_EXTERNAL, 
                                                    cv2.CHAIN_APPROX_NONE)

    # Sort them in x and y axis
    contours = group_and_sort_contours(contours)

    # cv2.imwrite("dilation.png", dilation)

    # Draw contours on the original image
    all_countours = cv2.drawContours(img.copy(), contours, -1, (255, 0, 0), 2)
    # cv2.imwrite("countours.png",all_countours)

    # Creating a copy of image
    im2 = img.copy()

    # List to store each row's text
    rows = []

    current_row = []
    prev_y = None
    tolerance = 15  # Tolerance to group contours into rows

    # Create a copy of the image to draw on
    output_img = img.copy()


    for cnt in contours:
        # Calculate moments of the contour
        M = cv2.moments(cnt)
        
        if M["m00"] != 0:  # Avoid division by zero
            # Calculate centroid coordinates
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            
            # Draw a green circle at the centroid
            cv2.circle(output_img, (cx, cy), 5, (0, 255, 0), -1)  # Green dot

            # Label the coordinates next to the centroid
            text = f"({cx},{cy})"
            cv2.putText(output_img, text, (cx -100, cy - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        x, y, w, h = cv2.boundingRect(cnt)
        # # Draw each rectangle on the image one by one
        # rect = cv2.rectangle(im2, (x, y), (x + w, y + h), (0, 255, 0), 2)
        # cv2.imshow("Rect", rect)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        
        # Crop the text block
        cropped = im2[y:y + h, x:x + w]
        
        # Apply OCR
        text = pytesseract.image_to_string(cropped).strip()
        
        if prev_y is None or abs(y - prev_y) < tolerance:
            current_row.append(text)
        else:
            rows.append(current_row)
            current_row = [text]
        
        prev_y = y

    # Append the last row
    if current_row:
        rows.append(current_row)

    # Print rows for verification
    # print(rows)

    # cv2.imwrite("centroids_with_labels.png", output_img)

    # Write to CSV
    with open(output_path, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)
        
if __name__ == "__main__":
    main()