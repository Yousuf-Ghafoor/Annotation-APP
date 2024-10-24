import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import zipfile
import random
import os
import yaml

# Set title
st.title("Annotation of the Images")

# File uploader for multiple image inputs
uploaded_files = st.file_uploader("Choose training images...", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    # Reverse the list to display the first uploaded image first
    uploaded_files = uploaded_files[::-1]

    # Initialize a dictionary to hold annotations for all images
    if 'all_annotations' not in st.session_state:
        st.session_state.all_annotations = {}

    # Initialize a dictionary to map defect names to consistent class IDs
    if 'defect_to_class_id' not in st.session_state:
        st.session_state.defect_to_class_id = {}

    # Initialize index for the current image
    if 'img_idx' not in st.session_state:
        st.session_state.img_idx = 0

    # Ensure the index doesn't go out of bounds
    if st.session_state.img_idx < 0:
        st.session_state.img_idx = 0
    if st.session_state.img_idx >= len(uploaded_files):
        st.session_state.img_idx = len(uploaded_files) - 1

    # Get the currently selected file
    selected_file = uploaded_files[st.session_state.img_idx]

    if selected_file:
        # Load the image into memory
        img = Image.open(selected_file)
        img_width, img_height = img.size  # Get image dimensions

        st.title(f"Name of the Image File: {selected_file.name}")

        # Create a canvas component for the selected image
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",  # Set the bounding box color
            stroke_width=2,
            stroke_color="#FF0000",  # Red color for bounding box border
            background_image=img,
            update_streamlit=True,
            drawing_mode="rect",  # Enable rectangle drawing
            key=selected_file.name,
        )

        # Initialize annotations for the current image if not already present
        if selected_file.name not in st.session_state.all_annotations:
            st.session_state.all_annotations[selected_file.name] = []

        # Store annotations based on user inputs
        if canvas_result.json_data is not None:
            for i, obj in enumerate(canvas_result.json_data["objects"]):
                if obj["type"] == "rect":
                    # Get bounding box coordinates and dimensions
                    x1 = obj["left"]
                    y1 = obj["top"]
                    width = obj["width"]
                    height = obj["height"]

                    # Normalize the bounding box coordinates
                    x_center = (x1 + width / 2) / img_width
                    y_center = (y1 + height / 2) / img_height
                    norm_width = width / img_width
                    norm_height = height / img_height

                    # Unique key for each defect name input
                    defect_name_key = f"defect_{selected_file.name}_{i}"

                    # Input field for defect name
                    defect_name = st.text_input(f"Name for defect in {selected_file.name} ({i + 1})", key=defect_name_key)

                    # Assign a consistent class ID for each defect name
                    if defect_name and defect_name not in st.session_state.defect_to_class_id:
                        # Assign the next available class ID
                        class_id = len(st.session_state.defect_to_class_id)
                        st.session_state.defect_to_class_id[defect_name] = class_id
                    elif defect_name:
                        # Use the existing class ID for the defect name
                        class_id = st.session_state.defect_to_class_id[defect_name]

                    # Store annotations only if a defect name is provided
                    if defect_name:
                        # Create the formatted annotation
                        annotation = f"{class_id} {x_center} {y_center} {norm_width} {norm_height}"

                        # Append only if it's not already in the session state
                        if annotation not in st.session_state.all_annotations[selected_file.name]:
                            st.session_state.all_annotations[selected_file.name].append(annotation)

        # Show the annotations for the current image
        if selected_file.name in st.session_state.all_annotations:
            for annotation in st.session_state.all_annotations[selected_file.name]:
                st.write(f"Annotation: {annotation}")

        # Create a column layout for navigation buttons
        col1, col2 = st.columns(2)

        # Function to move to the previous image
        def go_previous():
            if st.session_state.img_idx > 0:
                st.session_state.img_idx -= 1

        # Function to move to the next image
        def go_next():
            if st.session_state.img_idx < len(uploaded_files) - 1:
                st.session_state.img_idx += 1

        with col1:
            st.button("Previous", on_click=go_previous)

        with col2:
            st.button("Next", on_click=go_next)

        # Show the split ratio inputs when all images are annotated
        if st.session_state.img_idx == len(uploaded_files) - 1:
            st.subheader("Split Dataset")
            val_ratio = st.number_input("Validation Set Ratio (0.0 - 1.0)", min_value=0.0, max_value=1.0, value=0.2)
            test_ratio = st.number_input("Test Set Ratio (0.0 - 1.0)", min_value=0.0, max_value=1.0, value=0.1)

            # Ensure the total ratio does not exceed 1
            if st.button("Split Data"):
                total_ratio = val_ratio + test_ratio
                if total_ratio > 1.0:
                    st.error("Validation and Test ratios cannot exceed 1.0. Please adjust the ratios.")
                else:
                    # Shuffle uploaded files
                    random.shuffle(uploaded_files)

                    # Calculate split indices
                    total_files = len(uploaded_files)
                    val_split = int(total_files * val_ratio)
                    test_split = int(total_files * (val_ratio + test_ratio))

                    # Split the datasets
                    valid_images = uploaded_files[:val_split]
                    test_images = uploaded_files[val_split:test_split]
                    train_images = uploaded_files[test_split:]

                    # Show results of the split
                    st.success("Data split successfully!")
                    st.write(f"Training Images: {len(train_images)}")
                    st.write(f"Validation Images: {len(valid_images)}")
                    st.write(f"Test Images: {len(test_images)}")

                    # Create a single ZIP file for all datasets
                    def create_zip(images, annotations, folder_name):
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                            for file in images:
                                img = Image.open(file)
                                img_bytes = io.BytesIO()
                                img.save(img_bytes, format=img.format)
                                img_bytes.seek(0)
                                zip_file.writestr(f"{folder_name}/images/{file.name}", img_bytes.read())

                                if file.name in annotations:
                                    annotation_content = "\n".join(annotations[file.name])
                                    annotation_filename = file.name.replace(".jpg", ".txt").replace(".jpeg", ".txt").replace(".png", ".txt")
                                    zip_file.writestr(f"{folder_name}/labels/{annotation_filename}", annotation_content)

                        zip_buffer.seek(0)
                        return zip_buffer

                    # Create a single zip for all datasets
                    combined_zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(combined_zip_buffer, "w", zipfile.ZIP_DEFLATED) as combined_zip_file:
                        # Add training images and labels
                        for file in train_images:
                            img = Image.open(file)
                            img_bytes = io.BytesIO()
                            img.save(img_bytes, format=img.format)
                            img_bytes.seek(0)
                            combined_zip_file.writestr(f"train/images/{file.name}", img_bytes.read())

                            if file.name in st.session_state.all_annotations:
                                annotation_content = "\n".join(st.session_state.all_annotations[file.name])
                                annotation_filename = file.name.replace(".jpg", ".txt").replace(".jpeg", ".txt").replace(".png", ".txt")
                                combined_zip_file.writestr(f"train/labels/{annotation_filename}", annotation_content)

                        # Add validation images and labels
                        for file in valid_images:
                            img = Image.open(file)
                            img_bytes = io.BytesIO()
                            img.save(img_bytes, format=img.format)
                            img_bytes.seek(0)
                            combined_zip_file.writestr(f"valid/images/{file.name}", img_bytes.read())

                            if file.name in st.session_state.all_annotations:
                                annotation_content = "\n".join(st.session_state.all_annotations[file.name])
                                annotation_filename = file.name.replace(".jpg", ".txt").replace(".jpeg", ".txt").replace(".png", ".txt")
                                combined_zip_file.writestr(f"valid/labels/{annotation_filename}", annotation_content)

                        # Add test images and labels
                        for file in test_images:
                            img = Image.open(file)
                            img_bytes = io.BytesIO()
                            img.save(img_bytes, format=img.format)
                            img_bytes.seek(0)
                            combined_zip_file.writestr(f"test/images/{file.name}", img_bytes.read())

                            if file.name in st.session_state.all_annotations:
                                annotation_content = "\n".join(st.session_state.all_annotations[file.name])
                                annotation_filename = file.name.replace(".jpg", ".txt").replace(".jpeg", ".txt").replace(".png", ".txt")
                                combined_zip_file.writestr(f"test/labels/{annotation_filename}", annotation_content)

                         # Create the data.yaml file in the specified format
                        data_yaml = {
                            'train': '../train/images',
                            'val': '../valid/images',
                            'test': '../test/images',
                            'nc': len(st.session_state.defect_to_class_id),
                            'names': [name for name in st.session_state.defect_to_class_id.keys()]
                        }

                        # Format the names list as requested
                        formatted_names = "['" + "', '".join(data_yaml['names']) + "']"
                        combined_zip_file.writestr("data.yaml", f"train: ../train/images\nval: ../valid/images\ntest: ../test/images\n\nnc: {data_yaml['nc']}\nnames: {formatted_names}")

                        combined_zip_buffer.seek(0)

                        # Add README.txt file
                        readme_content = "This dataset contains images and annotations for defect detection.\n\n"
                        readme_content += "Put Your Own Dataset Directory in data.yaml file\n"
                        readme_content += "train : (own folder directory)\n"
                        readme_content += "val: (own folder directory)\n"
                        readme_content += "test: (own folder directory)\n"
                        readme_content += "\n"
                        readme_content += "\n"
                        readme_content += "Connect and Follow me on linked In\n"
                        readme_content += "https://www.linkedin.com/in/muhammad-yousuf-1a8580267/\n"
                        readme_content += "\n"
                        readme_content += "\n"
                        readme_content += "         Thank You       \n"
                        combined_zip_file.writestr("README.txt", readme_content)

                    combined_zip_buffer.seek(0)

                    # Provide a download link for the ZIP file
                    st.download_button(
                        label="Download Combined Dataset",
                        data=combined_zip_buffer,
                        file_name="combined_dataset.zip",
                        mime="application/zip"
                    )
