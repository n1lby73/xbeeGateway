Installation
============

Follow these steps to install the **XBee Gateway**:

.. note::

   It is **mandatory** to have MongoDB installed and running locally before starting the application.
   Without it, no configuration or historical data will be stored.

   Please refer to the official MongoDB documentation to set up MongoDB for your operating system:
   https://www.mongodb.com/docs/manual/installation/


**1. Clone the Repository**

   .. code-block:: bash

       git clone https://github.com/n1lby73/xbeeGateway.git
       cd xbeeGateway

**2. Set Up a Virtual Environment (Optional but Recommended)**

   .. code-block:: bash

       python3 -m venv venv
       source venv/bin/activate  # On Windows: venv\Scripts\activate

**3. Install Dependencies**

   .. code-block:: bash

       pip install -r requirements.txt

**4. Install Customized digi-xbee Library**

   .. code-block:: bash

       pip install git+https://github.com/n1lby73/xbee-python.git@exposeSerialSelection






